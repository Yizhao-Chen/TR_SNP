#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global ITRDB Detailed Metadata Fetcher
This script extracts detailed metadata from NOAA's enhanced RWL files for all available regions.
Creates consolidated metadata files for each region and a global summary.
All outputs are stored in the Test_version/metadata folder.
"""

import os
import sys
import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import argparse
import concurrent.futures
from statistics import mean
import logging
import json
import random
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


class GlobalDetailedMetadataFetcher:
    """Class to handle fetching detailed metadata from NOAA RWL files across all regions"""
    
    # List of all available regions in NOAA's repository
    REGIONS = [
        'africa', 
        'asia', 
        'atlantic', 
        'australia', 
        'centralamerica', 
        'europe', 
        'northamerica', 
        'southamerica'
    ]
    
    def __init__(self, regions=None, output_dir=None, site_pattern=None, max_workers=40,
                 cache_dir=None, retry_count=5, timeout=15, save_every=100,
                 skip_detailed=False, clear_cache=False, verbose=True, download_files=True):
        """Initialize the fetcher with configuration parameters"""
        # Base URL to tree ring data
        self.base_url = "https://www.ncei.noaa.gov/pub/data/paleo/treering/measurements/"
        
        # Set base directory to Test_version
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        
        # Check for environment variables for Docker compatibility
        env_cache_dir = os.environ.get('TR_SNP_CACHE_DIR')
        env_metadata_dir = os.environ.get('TR_SNP_METADATA_DIR')
        env_data_dir = os.environ.get('TR_SNP_DATA_DIR')
        
        # Set default metadata directory, prioritizing environment variable
        self.metadata_dir = env_metadata_dir or output_dir or os.path.join(self.base_dir, 'metadata')
        
        # Set default cache directory, prioritizing environment variable and falling back to temp dir if needed
        if env_cache_dir:
            self.cache_dir = env_cache_dir
        elif cache_dir:
            self.cache_dir = cache_dir
        else:
            # If no directories are explicitly provided, check if we're in a Docker container
            in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER')
            if in_docker and not os.access(self.base_dir, os.W_OK):
                # Inside Docker with no mounted volume, use temp directory
                import tempfile
                self.cache_dir = os.path.join(tempfile.gettempdir(), 'tr_snp_cache')
                print(f"Docker environment detected with no writable mounted volume. Using temporary cache: {self.cache_dir}")
            else:
                # Otherwise use the default location
                self.cache_dir = os.path.join(self.base_dir, 'cache')
        
        # Set default data directory for downloaded files, prioritizing environment variable
        self.data_dir = env_data_dir or os.path.join(self.metadata_dir, 'data')
        
        # Configuration values
        self.site_pattern = site_pattern
        self.verbose = verbose
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.timeout = timeout
        self.save_every = save_every
        self.skip_detailed = skip_detailed
        self.clear_cache = clear_cache
        self.download_files = download_files
        
        # Initialize start time for tracking execution duration
        self.start_time = time.time()
        
        # Initialize empty caches dictionary
        self.caches = {}
        
        # Set up logging first before any log calls
        self.setup_logging()
        
        # Make sure directories exist
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set the regions to process (default is all)
        self.regions = regions or self.REGIONS
        self.log_regions()
        
        # Create output file paths for each region
        self.output_files = {}
        for region in self.regions:
            self.output_files[region] = os.path.join(self.metadata_dir, f'{region}_detailed_metadata.csv')
        
        # Add global output file
        self.global_output_file = os.path.join(self.metadata_dir, 'global_detailed_metadata.csv')
        
        # Initialize session with retries
        self.session = self.create_session_with_retry()
        
        # Load caches
        self.caches = self.load_caches()
        
        # Clear cache if requested
        if self.clear_cache:
            self.clear_cache_data()
            
        # Log initialization
        self.log(f"Initialized global metadata fetcher")
        self.log(f"Base directory: {self.base_dir}")
        self.log(f"Metadata directory: {self.metadata_dir}")
        self.log(f"Cache directory: {self.cache_dir}")
        self.log(f"Global output file: {self.global_output_file}")
        self.log(f"Workers: {self.max_workers}")
        self.log(f"Retry count: {self.retry_count}")
    
    def log_regions(self):
        """Log the regions that will be processed"""
        if len(self.regions) == len(self.REGIONS):
            self.log(f"Processing all available regions: {', '.join(self.regions)}")
        else:
            self.log(f"Processing selected regions: {', '.join(self.regions)}")
            missing = [r for r in self.REGIONS if r not in self.regions]
            if missing:
                self.log(f"Skipping regions: {', '.join(missing)}", level='warning')
    
    def create_session_with_retry(self):
        """Create a requests session with automatic retry for failed requests"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=0.5,  # Exponential backoff
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # Add retry adapter to session with increased pool size to match worker count
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.max_workers,
            pool_maxsize=self.max_workers
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        })
        
        return session
    
    def setup_logging(self):
        """Set up logging for the script"""
        log_file = os.path.join(self.base_dir, 'global_metadata_fetch.log')
        
        # Reset logging handlers to avoid duplicate logs
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Create basic logging configuration with appropriate level
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Ensure both file and console output
        if not self.logger.handlers:
            # Add file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)
            
            # Add console handler - always use INFO level for console
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            self.logger.addHandler(console_handler)
        
        # Make sure the verbose flag doesn't suppress important console output
        if not self.verbose:
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    # Set to WARNING instead of CRITICAL to see warning messages
                    handler.setLevel(logging.WARNING)
    
    def log(self, message, level='info'):
        """Log message with appropriate level"""
        if level == 'debug':
            self.logger.debug(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        elif level == 'critical':
            self.logger.critical(message)
        else:
            self.logger.info(message)
    
    def load_caches(self):
        """Load previously processed files from cache for each region"""
        caches = {}
        for region in self.regions:
            cache_file = os.path.join(self.cache_dir, f'{region}_metadata_cache.json')
            caches[region] = {}
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        caches[region] = json.load(f)
                    self.log(f"Loaded cache for {region} with {len(caches[region])} previously processed files")
                except Exception as e:
                    self.log(f"Error loading cache for {region}: {e}", level='warning')
        return caches
    
    def save_cache(self, region):
        """Save processed files to cache for a specific region"""
        if region not in self.caches:
            self.log(f"No cache data for region {region}", level='warning')
            return
            
        cache_file = os.path.join(self.cache_dir, f'{region}_metadata_cache.json')
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.caches[region], f)
            self.log(f"Saved cache for {region} with {len(self.caches[region])} processed files")
        except Exception as e:
            self.log(f"Error saving cache for {region}: {e}", level='warning')
    
    def clear_cache_data(self):
        """Clear all cached data for all regions"""
        try:
            for region in self.regions:
                cache_file = os.path.join(self.cache_dir, f'{region}_metadata_cache.json')
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    self.log(f"Removed cache file for {region}: {cache_file}")
            
            # Clear the in-memory caches
            self.caches = {region: {} for region in self.regions}
            self.log("All cache data cleared")
        except Exception as e:
            self.log(f"Error clearing cache: {e}", level='error')

    def get_file_list(self, region):
        """Get list of NOAA RWL files from the specified region with retry logic
        Handle subdirectories specially, particularly for northamerica"""
        
        if region not in self.REGIONS:
            self.log(f"Invalid region: {region}", level='error')
            return []
            
        region_url = f"{self.base_url}{region}/"
        self.log(f"Accessing {region_url}")
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.get(region_url, timeout=self.timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                file_links = []
                
                # Check for directories (especially for northamerica which has subdirectories)
                subdirs = []
                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    
                    # Identify directory links (ending with '/')
                    if href.endswith('/') and href != '../':
                        # Remove trailing slash for subdirectory name
                        subdir = href[:-1]
                        subdirs.append(subdir)
                
                # Process files in current directory
                noaa_pattern = re.compile(r'^[a-z]{3}\d+-noaa\.rwl$')
                file_links.extend(self._process_directory_files(region, region_url, soup, noaa_pattern))
                
                # Process subdirectories if any
                if subdirs:
                    self.log(f"Found {len(subdirs)} subdirectories in {region}: {', '.join(subdirs)}")
                    for subdir in subdirs:
                        subdir_url = f"{region_url}{subdir}/"
                        self.log(f"Accessing subdirectory: {subdir_url}")
                        
                        # Fetch the subdirectory page
                        try:
                            subdir_response = self.session.get(subdir_url, timeout=self.timeout)
                            subdir_response.raise_for_status()
                            
                            subdir_soup = BeautifulSoup(subdir_response.text, 'html.parser')
                            subdir_files = self._process_directory_files(
                                region, 
                                subdir_url, 
                                subdir_soup, 
                                noaa_pattern,
                                subdir=subdir
                            )
                            file_links.extend(subdir_files)
                            
                        except requests.exceptions.RequestException as e:
                            self.log(f"Error accessing subdirectory {subdir_url}: {e}", level='error')
                
                self.log(f"Found {len(file_links)} NOAA RWL files in {region} directory/subdirectories")
                return file_links
                
            except requests.exceptions.RequestException as e:
                self.log(f"Error fetching {region} file list (attempt {attempt}/{max_attempts}): {e}", level='error')
                if attempt == max_attempts:
                    self.log(f"All attempts failed. Could not retrieve file list for {region}.", level='critical')
                    return []
                else:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.log(f"Retrying in {wait_time} seconds...", level='warning')
                    time.sleep(wait_time)
    
    def _process_directory_files(self, region, base_url, soup, noaa_pattern, subdir=None):
        """Process files in a directory or subdirectory and extract their metadata"""
        file_links = []
        
        # Dictionary to track files by site_id to handle both -noaa.rwl and -rwl-noaa.txt formats
        site_files = {}
        
        # Keep track of file formats found
        rwl_count = 0
        txt_count = 0
        skipped_count = 0
        
        self.log(f"Processing files from {base_url} (region: {region}, subdir: {subdir})", level='info')
        
        # Find all links on the page
        for link in soup.find_all('a'):
            href = link.get('href')
            
            # Filter for both NOAA RWL formats
            if href and ('-noaa.rwl' in href or '-rwl-noaa.txt' in href):
                # Filter by site pattern if specified
                if self.site_pattern and self.site_pattern not in href:
                    continue
                
                # Get the standard site ID depending on the file format
                if '-noaa.rwl' in href:
                    site_id = href.split('-noaa')[0]
                    rwl_count += 1
                    self.log(f"Found -noaa.rwl file: {href} (site_id: {site_id})", level='info')
                elif '-rwl-noaa.txt' in href:
                    site_id = href.split('-rwl-noaa')[0]
                    txt_count += 1
                    self.log(f"Found -rwl-noaa.txt file: {href} (site_id: {site_id})", level='info')
                else:
                    continue
                
                # Skip files with letter suffixes (e.g., morc019e, morc019l)
                if re.search(r'[a-z]+\d+[a-z]', site_id):
                    self.log(f"Skipping file with letter suffix in site ID: {site_id} (file: {href})", level='info')
                    skipped_count += 1
                    continue
                
                # Store the file info by site_id and format
                if site_id not in site_files:
                    site_files[site_id] = {}
                
                # Track the file type (-noaa.rwl has higher priority)
                if '-noaa.rwl' in href:
                    site_files[site_id]['noaa_rwl'] = href
                elif '-rwl-noaa.txt' in href:
                    site_files[site_id]['rwl_noaa_txt'] = href
        
        self.log(f"Statistics: found {rwl_count} -noaa.rwl files, {txt_count} -rwl-noaa.txt files, skipped {skipped_count} files", level='info')
        self.log(f"Total unique site IDs found: {len(site_files)}", level='info')
        
        # Process the collected files, prioritizing -noaa.rwl over -rwl-noaa.txt
        for site_id, formats in site_files.items():
            # Choose the file format, prioritizing -noaa.rwl
            if 'noaa_rwl' in formats:
                href = formats['noaa_rwl']
                self.log(f"Using -noaa.rwl format for {site_id}", level='info')
            elif 'rwl_noaa_txt' in formats:
                href = formats['rwl_noaa_txt']
                self.log(f"Using -rwl-noaa.txt format for {site_id} (no -noaa.rwl available)", level='info')
            else:
                # This shouldn't happen but just in case
                continue
                
            country_code = site_id[:3].lower() if len(site_id) >= 3 else 'unknown'
            
            # Modified URL based on whether this is in a subdirectory
            file_url = f"{base_url}{href}"
            
            # Create a cache key that includes the region and subdirectory if applicable
            cache_key = f"{region}_{site_id}" if subdir is None else f"{region}_{subdir}_{site_id}"
            
            # Check if file is already in cache
            if region in self.caches and cache_key in self.caches[region] and not self.skip_detailed:
                self.log(f"Using cached data for {site_id} in {region}", level='debug')
                file_links.append(self.caches[region][cache_key])
                continue
            
            # Determine the standard file name based on the site ID
            standard_file = f"{site_id}.rwl"
            
            # Store URLs for both potential file formats
            noaa_rwl_url = f"{base_url}{formats['noaa_rwl']}" if 'noaa_rwl' in formats else None
            rwl_noaa_txt_url = f"{base_url}{formats['rwl_noaa_txt']}" if 'rwl_noaa_txt' in formats else None
            
            file_info = {
                'site_id': site_id,
                'filename': href,  # Primary file name chosen based on priority
                'url': file_url,    # Primary URL chosen based on priority
                'noaa_rwl_url': noaa_rwl_url,
                'rwl_noaa_txt_url': rwl_noaa_txt_url,
                'standard_file': standard_file,
                'standard_url': f"{base_url}{standard_file}",
                'region': region,
                'subdir': subdir,  # Will be None for files not in subdirectories
                'country_code': country_code,
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }
            
            file_links.append(file_info)
        
        return file_links

    def get_all_files(self):
        """Get file lists from all specified regions"""
        all_files = {}
        total_files = 0
        
        for region in self.regions:
            self.log(f"Fetching file list for {region}...")
            region_files = self.get_file_list(region)
            all_files[region] = region_files
            total_files += len(region_files)
            self.log(f"Found {len(region_files)} files in {region}")
        
        self.log(f"Total NOAA files found across all regions: {total_files}")
        return all_files
    
    def fetch_file_content(self, file_info):
        """Fetch content of a NOAA RWL file with enhanced error handling"""
        site_id = file_info['site_id']
        filename = file_info['filename']
        url = file_info['url']
        region = file_info['region']
        
        # Skip detailed fetching if requested
        if self.skip_detailed:
            return None
        
        # Create a cache key that includes the region and subdirectory if applicable
        subdir = file_info.get('subdir')

        cache_key = f"{region}_{site_id}" if subdir is None else f"{region}_{subdir}_{site_id}"
        
        # Check if we already have cached data for this file
        if region in self.caches and cache_key in self.caches[region]:
            self.log(f"Using cached data for {filename} in {region}", level='debug')
            return "CACHED"  # Special marker to indicate we use cached data
        
        try:
            # Fetch the file with built-in retry logic from the session
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.text
            else:
                self.log(f"Failed to fetch {filename}: HTTP {response.status_code}", level='warning')
                return None
                
        except requests.exceptions.RequestException as e:
            self.log(f"Error fetching {filename}: {e}", level='error')
            return None
    
    def extract_metadata_from_noaa(self, file_content, file_info):
        """Extract detailed metadata from NOAA RWL file content"""
        site_id = file_info['site_id']
        region = file_info['region']
        subdir = file_info.get('subdir')

        # Create a cache key that includes the region and subdirectory if applicable
        cache_key = f"{region}_{site_id}" if subdir is None else f"{region}_{subdir}_{site_id}"
        
        # Use cached data if available
        if region in self.caches and cache_key in self.caches[region]:
            self.log(f"Using cached metadata for {site_id} in {region}", level='debug')
            return self.caches[region][cache_key]
        
        # Skip detailed extraction if requested or no content
        if self.skip_detailed or not file_content or file_content == "CACHED":
            return file_info
        
        # Start with basic file info
        metadata = file_info.copy()
        
        try:
            # Extract key metadata fields
            # Investigators
            investigators_match = re.search(r'INVESTIGATORS?[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if investigators_match:
                metadata['investigators'] = investigators_match.group(1).strip()
            
            # Site Name
            site_name_match = re.search(r'SITE_NAME[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if site_name_match:
                metadata['site_name'] = site_name_match.group(1).strip()
            
            # Latitude (calculate mean if both northernmost and southernmost are provided)
            northlat_match = re.search(r'NORTHERNMOST_LATITUDE[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            southlat_match = re.search(r'SOUTHERNMOST_LATITUDE[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            lat_match = re.search(r'(?:LATITUDE|LAT)[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            
            if northlat_match and southlat_match:
                north_lat = float(northlat_match.group(1))
                south_lat = float(southlat_match.group(1))
                metadata['latitude'] = mean([north_lat, south_lat])
                metadata['northernmost_latitude'] = north_lat
                metadata['southernmost_latitude'] = south_lat
            elif lat_match:
                metadata['latitude'] = float(lat_match.group(1))
            
            # Longitude (calculate mean if both easternmost and westernmost are provided)
            eastlon_match = re.search(r'EASTERNMOST_LONGITUDE[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            westlon_match = re.search(r'WESTERNMOST_LONGITUDE[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            lon_match = re.search(r'(?:LONGITUDE|LON)[\s:]+([0-9.-]+)', file_content, re.IGNORECASE)
            
            if eastlon_match and westlon_match:
                east_lon = float(eastlon_match.group(1))
                west_lon = float(westlon_match.group(1))
                metadata['longitude'] = mean([east_lon, west_lon])
                metadata['easternmost_longitude'] = east_lon
                metadata['westernmost_longitude'] = west_lon
            elif lon_match:
                metadata['longitude'] = float(lon_match.group(1))
            
            # Elevation - modified to include Elevation_m: format
            elevation_match = None
            elevation_patterns = [
                r'(?:ELEVATION|ELEV)[\s:]+([0-9.-]+)',
                r'Elevation_m:\s*([0-9.-]+)'
            ]
            for pattern in elevation_patterns:
                match = re.search(pattern, file_content, re.IGNORECASE)
                if match:
                    metadata['elevation'] = float(match.group(1))
                    self.log(f"Found elevation using pattern '{pattern}': {match.group(1)}", level='debug')
                    break
            
            # Species information - Clean up by removing "#Species_Name:" prefix
            # Species information - Clean up by removing "#Species_Name:" prefix
            species_match = None
            
            # First try to extract from the specific Species section header
            section_pattern = r'#--------------------\s+#\s*Species\s+#\s*Species_Name:\s+([^\n]+)'
            section_match = re.search(section_pattern, file_content, re.IGNORECASE)
            
            if section_match:
                species_text = section_match.group(1).strip()
                metadata['species_name'] = species_text
                self.log(f"Found species name from dedicated Species section: {species_text}", level='debug')
            else:
                # If section header not found, try traditional patterns but in a better order
                species_patterns = [
                    r'#\s*Species_Name:\s+([^\n]+)',
                    r'Species_Name:?\s+([^\n]+)',
                    r'SPECIES[\s:]+([^\n]+)'
                ]
                
                for pattern in species_patterns:
                    match = re.search(pattern, file_content, re.IGNORECASE)
                    if match:
                        species_text = match.group(1).strip()
                        # Remove "#Species_Name:" prefix if present
                        species_text = re.sub(r'^#\s*Species_Name:\s*', '', species_text)
                        # Also remove just "#" if that's all that's left
                        species_text = re.sub(r'^#\s*$', '', species_text)
                        metadata['species_name'] = species_text
                        self.log(f"Found species name using pattern '{pattern}': {species_text}", level='debug')
                        break
            
            # Validate species name - if too long, it's likely part of Abstract or other text
            if 'species_name' in metadata and len(metadata['species_name']) > 100:
                self.log(f"Species name too long ({len(metadata['species_name'])} chars), likely from Abstract", level='warning')
                
                # Try a line-by-line approach for a more precise extraction
                species_found = False
                species_section = False
                
                for line in file_content.split('\n'):
                    # Check for a Species section marker
                    if re.search(r'#-+\s*#\s*Species\s*$', line, re.IGNORECASE):
                        species_section = True
                        continue
                    
                    # If in the Species section, look for the Species_Name line
                    if species_section and 'Species_Name:' in line:
                        parts = line.split('Species_Name:', 1)
                        if len(parts) > 1:
                            species_text = parts[1].strip()
                            metadata['species_name'] = species_text
                            species_found = True
                            self.log(f"Reset species name using line-by-line search: {species_text}", level='debug')
                            break
                    
                    # If we've moved past the Species section, stop looking
                    if species_section and '#--------------------' in line:
                        species_section = False
                
                # If we still couldn't find a better species name, remove the overly long one
                if not species_found and 'species_name' in metadata:
                    self.log(f"Could not find valid species name, removing potentially incorrect value", level='warning')
                    metadata.pop('species_name', None)
            
            # Common Name - find and clean properly
            common_name_match = re.search(r'COMMON_NAME[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if common_name_match:
                common_name = common_name_match.group(1).strip()
                # Remove any "Tree_Species_Code:" content that may have been included in common_name
                common_name = re.sub(r'#\s*Tree_Species_Code:\s*[\w]+', '', common_name).strip()
                metadata['common_name'] = common_name
            
            # Tree Species Code
            species_code_match = re.search(r'TREE_SPECIES_CODE[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if species_code_match:
                metadata['tree_species_code'] = species_code_match.group(1).strip()
            
            # Publication/Reference information - collect all components
            publication_parts = {}
            
            # Enhanced reference extraction - gather all possible citation components
            publication_match = re.search(r'PUBLICATION[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if publication_match:
                publication_parts['publication'] = publication_match.group(1).strip()
            
            authors_match = re.search(r'AUTHORS?[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if authors_match:
                publication_parts['authors'] = authors_match.group(1).strip()
            
            journal_match = re.search(r'JOURNAL(?:_NAME)?[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if journal_match:
                publication_parts['journal'] = journal_match.group(1).strip()
            
            # Improved title extraction - more aggressive about finding the title
            published_title = None
            
            # Try multiple patterns for Published_Title with more explicit logging
            title_patterns = [
                (r'(?:^|\n)#?\s*PUBLISHED_TITLE[\s:]+([^\n]+)', 'PUBLISHED_TITLE field'),
                (r'(?:^|\n)#?\s*Published_Title:?\s*([^\n]+)', 'Published_Title field'),
                (r'(?:^|\n)#?\s*TITLE[\s:]+([^\n]+)', 'TITLE field'),
                (r'(?:^|\n)#?\s*Title:?\s*([^\n]+)', 'Title field'),
                (r'(?:^|\n)STUDY\s+TITLE:?\s*([^\n]+)', 'STUDY TITLE field')
            ]
            
            for pattern, desc in title_patterns:
                match = re.search(pattern, file_content, re.IGNORECASE)
                if match:
                    candidate = match.group(1).strip()
                    # Clean up Study_Name prefix if present
                    if 'Study_Name:' in candidate:
                        candidate = re.sub(r'Study_Name:\s*', '', candidate).strip()
                    
                    published_title = candidate
                    self.log(f"Found title from {desc} for {site_id}: {published_title}", level='debug')
                    publication_parts['title'] = published_title
                    break
            
            # Pages extraction with better logging
            pages_text = None
            pages_patterns = [
                (r'(?:^|\n)#?\s*PAGES[\s:]+([^\n]+)', 'PAGES field'),
                (r'(?:^|\n)#?\s*Pages:?\s*([^\n]+)', 'Pages field'),
                (r'(?:^|\n)PAGE[\s:]+([^\n]+)', 'PAGE field'),
                (r'(?:^|\n)Page:?\s*([^\n]+)', 'Page field')
            ]
            
            for pattern, desc in pages_patterns:
                match = re.search(pattern, file_content, re.IGNORECASE)
                if match:
                    pages_text = match.group(1).strip()
                    self.log(f"Found pages from {desc} for {site_id}: {pages_text}", level='debug')
                    publication_parts['pages'] = pages_text
                    break
            
            year_match = re.search(r'(?:PUBLISHED_DATE|PUBLISHED_YEAR|PUBLICATION_YEAR|PUBLISHED_DATE_OR_YEAR)[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if year_match:
                publication_parts['year'] = year_match.group(1).strip()
            
            volume_match = re.search(r'VOLUME[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if volume_match:
                publication_parts['volume'] = volume_match.group(1).strip()
            
            issue_match = re.search(r'ISSUE[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if issue_match:
                publication_parts['issue'] = issue_match.group(1).strip()
                
            doi_match = re.search(r'DOI[\s:]+([^\n]+)', file_content, re.IGNORECASE)
            if doi_match:
                publication_parts['doi'] = doi_match.group(1).strip()
            
            # Combine all publication parts into a single reference field in a comprehensive format
            if publication_parts:
                # Create reference string as specifically requested
                reference_components = []
                
                # Authors
                if 'authors' in publication_parts:
                    reference_components.append(f"Authors: {publication_parts['authors']}")
                
                # Journal
                if 'journal' in publication_parts:
                    reference_components.append(f"Journal_Name: {publication_parts['journal']}")
                
                # Title - ensure it's explicitly labeled as Published_Title
                if 'title' in publication_parts:
                    # Ensure the "Published_Title:" prefix is explicitly included
                    title = publication_parts['title']
                    if title:
                        reference_components.append(f"Published_Title: {title}")
                
                # Year
                if 'year' in publication_parts:
                    reference_components.append(f"Published_Date_or_Year: {publication_parts['year']}")
                
                # Volume
                if 'volume' in publication_parts:
                    reference_components.append(f"Volume: {publication_parts['volume']}")
                
                # Pages - ensure it's explicitly labeled as Pages
                if 'pages' in publication_parts:
                    # Ensure the "Pages:" prefix is explicitly included
                    pages = publication_parts['pages']
                    if pages:
                        reference_components.append(f"Pages: {pages}")
                
                # DOI
                if 'doi' in publication_parts:
                    reference_components.append(f"DOI: {publication_parts['doi']}")
                
                # Check if we have any components, use publication field as fallback
                if reference_components:
                    metadata['reference'] = ', '.join(reference_components)
                elif 'publication' in publication_parts:
                    # Clean publication field if using as fallback
                    pub_text = publication_parts['publication']
                    pub_text = re.sub(r'Study_Name:[^,]*,?\s*', '', pub_text).strip()
                    metadata['reference'] = pub_text
            
            # Extract first_year and last_year information
            # First look for Earliest_Year and Most_Recent_Year fields with exact format "# Earliest_Year:" and "# Most_Recent_Year:"
            # Update patterns to handle negative years (BCE dates)
            earliest_year_match = re.search(r'#\s*Earliest_Year:\s*(-?\d{1,4})', file_content)
            most_recent_year_match = re.search(r'#\s*Most_Recent_Year:\s*(-?\d{1,4})', file_content)
            
            # If found, use these values directly as they're the preferred source
            if earliest_year_match:
                metadata['first_year'] = float(earliest_year_match.group(1))
                self.log(f"Found first_year ({metadata['first_year']}) from exact pattern '#Earliest_Year:'", level='debug')
            
            if most_recent_year_match:
                metadata['last_year'] = float(most_recent_year_match.group(1))
                self.log(f"Found last_year ({metadata['last_year']}) from exact pattern '#Most_Recent_Year:'", level='debug')
            
            # Only if exact patterns not found, try more flexible patterns
            if 'first_year' not in metadata or 'last_year' not in metadata:
                year_patterns = [
                    # Lowercase variants - updated to handle negative years
                    (r'(?:^|\n)#?\s*Earliest[_\s]*Year[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*Most[_\s]*Recent[_\s]*Year[\s:]+(-?\d{1,4})', 'last_year'),
                    # Uppercase patterns - updated to handle negative years
                    (r'(?:^|\n)#?\s*EARLIEST_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*FIRST_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*BEGINNING_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*START_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*MOST_RECENT_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*LAST_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*ENDING_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*END_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    # Additional patterns for various formats - updated to handle negative years
                    (r'(?:^|\n)(?:#\s*)?(?:CHRON|CHRONOLOGY)\s+STARTS\s+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:CHRON|CHRONOLOGY)\s+ENDS\s+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:DATA|DATA\s+SET)\s+STARTS\s+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:DATA|DATA\s+SET)\s+ENDS\s+(-?\d{1,4})', 'last_year')
                ]
                
                for pattern, field in year_patterns:
                    match = re.search(pattern, file_content, re.IGNORECASE)
                    if match:
                        year_value = int(match.group(1))
                        if field == 'first_year' and 'first_year' not in metadata:
                            metadata['first_year'] = year_value
                            self.log(f"Found first_year ({year_value}) using flexible pattern", level='debug')
                        elif field == 'last_year' and 'last_year' not in metadata:
                            metadata['last_year'] = year_value
                            self.log(f"Found last_year ({year_value}) using flexible pattern", level='debug')
            
            # Cache successful extraction
            if region not in self.caches:
                self.caches[region] = {}
            self.caches[region][cache_key] = metadata
            
            return metadata
            
        except Exception as e:
            self.log(f"Error extracting metadata from {file_info['filename']}: {e}", level='error')
            return file_info
    
    def inspect_raw_content(self, file_info):
        """Directly inspect raw file content to better extract metadata fields
        This is a deeper inspection that examines the raw file and tries various 
        approaches to extract hard-to-find fields"""
        url = file_info.get('url')
        site_id = file_info.get('site_id', 'unknown')
        
        if not url:
            return None
            
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
                
            content = response.text
            
            # Look for unique patterns of Published_Title in the raw content
            title_patterns = [
                r'(?:^|\n)(?:#\s*)?Published[\s_-]Title:?\s*([^\n]+)',
                r'(?:^|\n)(?:#\s*)?Title:?\s*([^\n]+)',
                r'(?:^|\n)TITLE\s*=\s*([^\n]+)',
                r'(?:^|\n)(?:#\s*)?STUDY\s+TITLE:?\s*([^\n]+)'
            ]
            
            title = None
            for pattern in title_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    self.log(f"[Inspection] Found title for {site_id}: {title}", level='debug')
                    break
         
            # Look for unique patterns of Pages in the raw content
            pages_patterns = [
                r'(?:^|\n)(?:#\s*)?Pages?:?\s*([^\n]+)',
                r'(?:^|\n)PAGES?\s*=\s*([^\n]+)'
            ]
            
            pages = None
            for pattern in pages_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    pages = match.group(1).strip()
                    self.log(f"[Inspection] Found pages for {site_id}: {pages}", level='debug')
                    break
         
            # Look for species names that might have been missed
            species_patterns = [
                r'(?:^|\n)(?:#\s*)?Species_Name:?\s*([^\n]+)',
                r'(?:^|\n)SPECIES\s*=\s*([^\n]+)',
                r'(?:^|\n)(?:#\s*)?Species:?\s*([^\n]+)'
            ]
            
            species_name = None
            for pattern in species_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    species_name = match.group(1).strip()
                    # Clean up species name
                    if species_name.startswith('#'):
                        species_name = species_name[1:].strip()
                    if species_name:
                        self.log(f"[Inspection] Found species name for {site_id}: {species_name}", level='debug')
                        break
         
            # Look for year information with improved patterns
            # First try exact format match for "# Earliest_Year:" and "# Most_Recent_Year:"
            earliest_year_match = re.search(r'#\s*Earliest_Year:\s*(-?\d{1,4})', content)
            most_recent_year_match = re.search(r'#\s*Most_Recent_Year:\s*(-?\d{1,4})', content)
            
            first_year = None
            last_year = None
            
            if earliest_year_match:
                first_year = int(earliest_year_match.group(1))
                self.log(f"[Inspection] Found first year for {site_id} with exact pattern: {first_year}", level='debug')
            
            if most_recent_year_match:
                last_year = int(most_recent_year_match.group(1))
                self.log(f"[Inspection] Found last year for {site_id} with exact pattern: {last_year}", level='debug')
            
            # Only if exact patterns not found, try more flexible patterns
            if not first_year or not last_year:
                year_patterns = [
                    # Lowercase variants - updated to handle negative years
                    (r'(?:^|\n)#?\s*Earliest[_\s]*Year[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*Most[_\s]*Recent[_\s]*Year[\s:]+(-?\d{1,4})', 'last_year'),
                    # Uppercase patterns - updated to handle negative years
                    (r'(?:^|\n)#?\s*EARLIEST_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*FIRST_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*BEGINNING_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*START_YEAR[\s:]+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)#?\s*MOST_RECENT_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*LAST_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*ENDING_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)#?\s*END_YEAR[\s:]+(-?\d{1,4})', 'last_year'),
                    # Additional patterns for various formats - updated to handle negative years
                    (r'(?:^|\n)(?:#\s*)?(?:CHRON|CHRONOLOGY)\s+STARTS\s+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:CHRON|CHRONOLOGY)\s+ENDS\s+(-?\d{1,4})', 'last_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:DATA|DATA\s+SET)\s+STARTS\s+(-?\d{1,4})', 'first_year'),
                    (r'(?:^|\n)(?:#\s*)?(?:DATA|DATA\s+SET)\s+ENDS\s+(-?\d{1,4})', 'last_year')
                ]
                
                for pattern, field in year_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        year_value = int(match.group(1))
                        if field == 'first_year' and not first_year:
                            first_year = year_value
                            self.log(f"[Inspection] Found first year for {site_id} with flexible pattern: {first_year}", level='debug')
                        elif field == 'last_year' and not last_year:
                            last_year = year_value
                            self.log(f"[Inspection] Found last year for {site_id} with flexible pattern: {last_year}", level='debug')
            
            # If still missing years, try year range patterns
            if not first_year or not last_year:
                # Update patterns to handle negative years
                year_range_patterns = [
                    r'(-?\d{1,4})\s+TO\s+(-?\d{1,4})',
                    r'Years:\s+(-?\d{1,4})\s*-\s*(-?\d{1,4})',
                    r'(?:^|\n)#?\s*Year\s+Range:\s*(-?\d{1,4})\s*-\s*(-?\d{1,4})',
                    r'(?:^|\n)#?\s*Time\s+Span:\s*(-?\d{1,4})\s*-\s*(-?\d{1,4})',
                    r'(?:^|\n)#?\s*Span:\s*(-?\d{1,4})\s*-\s*(-?\d{1,4})',
                    r'from\s+(-?\d{1,4})\s+to\s+(-?\d{1,4})',
                    r'spanning\s+(-?\d{1,4})\s*(?:-|to)\s*(-?\d{1,4})',
                    r'data\s+spans?\s+(-?\d{1,4})\s*(?:-|to)\s*(-?\d{1,4})',
                    r'period\s+(-?\d{1,4})\s*(?:-|to)\s*(-?\d{1,4})'
                ]
                
                for pattern in year_range_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        if not first_year:
                            first_year = int(match.group(1))
                            self.log(f"[Inspection] Extracted first_year from range for {site_id}: {first_year}", level='debug')
                        
                        if not last_year:
                            last_year = int(match.group(2))
                            self.log(f"[Inspection] Extracted last_year from range for {site_id}: {last_year}", level='debug')
                        
                        break
            
            # Return results
            results = {}
            if title:
                results['published_title'] = title
            if pages:
                results['pages'] = pages
            if species_name:
                results['species_name'] = species_name
            if first_year:
                results['first_year'] = float(first_year)
            if last_year:
                results['last_year'] = float(last_year)
            
            return results
            
        except Exception as e:
            self.log(f"Error inspecting raw content for {site_id}: {e}", level='error')
            return None
    
    def download_rwl_file(self, file_info):
        """Download a .rwl file to the data directory"""
        if not self.download_files:
            return
            
        site_id = file_info['site_id']
        region = file_info['region']
        subdir = file_info.get('subdir')

        # Create region directory if needed
        region_dir = os.path.join(self.data_dir, region)
        if subdir:
            region_dir = os.path.join(region_dir, subdir)
        os.makedirs(region_dir, exist_ok=True)
        
        # Determine the target file path
        target_file = os.path.join(region_dir, f"{site_id}.rwl")
        
        # Skip if file already exists
        if os.path.exists(target_file):
            self.log(f"File already exists: {target_file}", level='debug')
            return
            
        # Get the source URL (using the standard URL without NOAA suffix)
        source_url = file_info['standard_url']
        
        try:
            # Download the file
            response = self.session.get(source_url, timeout=self.timeout)
            if response.status_code == 200:
                with open(target_file, 'wb') as f:
                    f.write(response.content)
                self.log(f"Downloaded {site_id}.rwl to {target_file}", level='info')
            else:
                self.log(f"Failed to download {site_id}.rwl: HTTP {response.status_code}", level='warning')
        except Exception as e:
            self.log(f"Error downloading {site_id}.rwl: {e}", level='error')

    def process_file(self, file_info):
        """Process a single file to extract detailed metadata with robust error handling"""
        site_id = file_info['site_id']
        filename = file_info['filename']
        region = file_info['region']
        subdir = file_info.get('subdir')
        
        # Download the .rwl file if requested - moved to the beginning to always run regardless of cache
        if self.download_files:
            self.download_rwl_file(file_info)
        
        # Create a cache key that includes the region and subdirectory if applicable
        cache_key = f"{region}_{site_id}" if subdir is None else f"{region}_{subdir}_{site_id}"
        
        # Check if file is already in cache
        if region in self.caches and cache_key in self.caches[region] and not self.skip_detailed:
            self.log(f"Using cached data for {filename} in {region}", level='debug')
            return self.caches[region][cache_key]
        
        self.log(f"Processing {filename} from {region}", level='debug')
        
        try:
            # Skip detailed processing if requested
            if self.skip_detailed:
                return file_info
            
            # Special handling for species name extraction - try rwl-noaa.txt file first
            rwl_noaa_txt_url = file_info.get('rwl_noaa_txt_url')
            noaa_rwl_url = file_info.get('noaa_rwl_url')
            
            metadata = file_info.copy()
            valid_species_name = None
            valid_common_name = None
            valid_tree_species_code = None
            
            # Check the rwl-noaa.txt file first for species name if available
            if rwl_noaa_txt_url:
                self.log(f"Trying rwl-noaa.txt file first for species data: {rwl_noaa_txt_url}", level='debug')
                
                try:
                    # Fetch the rwl-noaa.txt file content
                    alt_file_info = file_info.copy()
                    alt_file_info['url'] = rwl_noaa_txt_url
                    txt_content = self.fetch_file_content(alt_file_info)
                    
                    if txt_content and txt_content != "CACHED":
                        # Extract species name from the txt file
                        species_match = None
                        
                        # First try to extract from the specific Species section header
                        section_pattern = r'#--------------------\s+#\s*Species\s+#\s*Species_Name:\s+([^\n]+)'
                        section_match = re.search(section_pattern, txt_content, re.IGNORECASE)
                        
                        if section_match:
                            species_text = section_match.group(1).strip()
                            valid_species_name = species_text
                            self.log(f"Found species name from rwl-noaa.txt file: {valid_species_name}", level='info')
                        else:
                            # If section header not found, try traditional patterns
                            species_patterns = [
                                r'#\s*Species_Name:\s+([^\n]+)',
                                r'Species_Name:?\s+([^\n]+)',
                                r'SPECIES[\s:]+([^\n]+)'
                            ]
                            
                            for pattern in species_patterns:
                                match = re.search(pattern, txt_content, re.IGNORECASE)
                                if match:
                                    species_text = match.group(1).strip()
                                    # Remove "#Species_Name:" prefix if present
                                    species_text = re.sub(r'^#\s*Species_Name:\s*', '', species_text)
                                    # Also remove just "#" if that's all that's left
                                    species_text = re.sub(r'^#\s*$', '', species_text)
                                    
                                    # Validate the species name - if it's too long or contains certain keywords,
                                    # it's likely not a valid species name
                                    if len(species_text) <= 100 and not re.search(r'(case study|reconstruction|abstract|title|publication)', species_text, re.IGNORECASE):
                                        valid_species_name = species_text
                                        self.log(f"Found species name from rwl-noaa.txt using pattern '{pattern}': {valid_species_name}", level='info')
                                        break
                        
                        # Extract common_name from the txt file
                        common_name_match = re.search(r'COMMON_NAME[\s:]+([^\n]+)', txt_content, re.IGNORECASE)
                        valid_common_name = None
                        if common_name_match:
                            common_name = common_name_match.group(1).strip()
                            # Remove any "Tree_Species_Code:" content that may have been included in common_name
                            common_name = re.sub(r'#\s*Tree_Species_Code:\s*[\w]+', '', common_name).strip()
                            valid_common_name = common_name
                            self.log(f"Found common name from rwl-noaa.txt file: {valid_common_name}", level='info')
                        
                        # Extract tree_species_code from the txt file
                        species_code_match = re.search(r'TREE_SPECIES_CODE[\s:]+([^\n]+)', txt_content, re.IGNORECASE)
                        valid_tree_species_code = None
                        if species_code_match:
                            valid_tree_species_code = species_code_match.group(1).strip()
                            self.log(f"Found tree species code from rwl-noaa.txt file: {valid_tree_species_code}", level='info')
                except Exception as e:
                    self.log(f"Error extracting species data from rwl-noaa.txt: {e}", level='warning')
            
            # Fetch the file content for the primary URL (as per the original file_info)
            file_content = self.fetch_file_content(file_info)
            
            if file_content:
                # Extract metadata from the primary file
                metadata = self.extract_metadata_from_noaa(file_content, file_info)
                
                # If we found a valid species name from the rwl-noaa.txt file, use it
                if valid_species_name:
                    metadata['species_name'] = valid_species_name
                    self.log(f"Using species name from rwl-noaa.txt file for {site_id}: {valid_species_name}", level='info')
                
                # If we found a valid common name from the rwl-noaa.txt file, use it
                if valid_common_name:
                    metadata['common_name'] = valid_common_name
                    self.log(f"Using common name from rwl-noaa.txt file for {site_id}: {valid_common_name}", level='info')
                
                # If we found a valid tree species code from the rwl-noaa.txt file, use it
                if valid_tree_species_code:
                    metadata['tree_species_code'] = valid_tree_species_code
                    self.log(f"Using tree species code from rwl-noaa.txt file for {site_id}: {valid_tree_species_code}", level='info')
                
                # Otherwise, check if we should try to get the species name from the alternative file
                else:
                    primary_species = metadata.get('species_name')
                    is_invalid_species = (
                        not primary_species or 
                        len(primary_species) > 100 or 
                        re.search(r'(case study|reconstruction|abstract|title|publication)', primary_species, re.IGNORECASE)
                    )
                    
                    # Check if we need to try the alternative file for any of the species info
                    primary_common_name = metadata.get('common_name')
                    primary_tree_species_code = metadata.get('tree_species_code')
                    
                    need_alt_file = (
                        is_invalid_species or 
                        (not primary_common_name) or 
                        (not primary_tree_species_code)
                    )
                    
                    if need_alt_file:
                        self.log(f"One or more species data fields missing or invalid for {site_id}. Checking alternative file.", level='debug')
                        
                        alt_url = None
                        # Determine the alternative URL
                        if file_info.get('noaa_rwl_url') == file_info['url'] and rwl_noaa_txt_url:
                            alt_url = rwl_noaa_txt_url  # Primary was .rwl, try .txt
                        elif file_info.get('rwl_noaa_txt_url') == file_info['url'] and noaa_rwl_url:
                            alt_url = noaa_rwl_url      # Primary was .txt, try .rwl
                        
                        if alt_url:
                            self.log(f"Fetching alternative file: {alt_url}", level='debug')
                            # Create a temporary file_info for fetching alternative content
                            alt_file_info = file_info.copy()
                            alt_file_info['url'] = alt_url
                            alt_file_info['filename'] = alt_url.split('/')[-1]
                            
                            alt_content = self.fetch_file_content(alt_file_info)
                            
                            if alt_content and alt_content != "CACHED": # Don't re-extract if cached
                                self.log(f"Extracting metadata from alternative file for {site_id}", level='debug')
                                alt_metadata = self.extract_metadata_from_noaa(alt_content, alt_file_info)
                                
                                # Check for species name
                                if is_invalid_species:
                                    alt_species = alt_metadata.get('species_name')
                                    
                                    # Check if the alternative species name is valid
                                    is_valid_alt_species = (
                                        alt_species and 
                                        len(alt_species) <= 100 and 
                                        not re.search(r'(case study|reconstruction|abstract|title|publication)', alt_species, re.IGNORECASE)
                                    )
                                    
                                    if is_valid_alt_species:
                                        self.log(f"Found valid species name '{alt_species}' in alternative file for {site_id}. Updating.", level='info')
                                        metadata['species_name'] = alt_species
                                    else:
                                        self.log(f"Alternative file for {site_id} also had invalid species name ('{alt_species}'). Keeping primary.", level='debug')
                                
                                # Check for common name
                                if not primary_common_name:
                                    alt_common_name = alt_metadata.get('common_name')
                                    if alt_common_name:
                                        self.log(f"Found common name '{alt_common_name}' in alternative file for {site_id}. Updating.", level='info')
                                        metadata['common_name'] = alt_common_name
                                
                                # Check for tree species code
                                if not primary_tree_species_code:
                                    alt_tree_species_code = alt_metadata.get('tree_species_code')
                                    if alt_tree_species_code:
                                        self.log(f"Found tree species code '{alt_tree_species_code}' in alternative file for {site_id}. Updating.", level='info')
                                        metadata['tree_species_code'] = alt_tree_species_code
                            elif alt_content == "CACHED":
                                 self.log(f"Alternative file content for {site_id} was cached, skipping re-extraction.", level='debug')
                            else:
                                self.log(f"Could not fetch content for alternative file: {alt_url}", level='warning')
                        else:
                            self.log(f"No alternative file URL found for {site_id}", level='debug')

                # Always perform deeper inspection to catch missing fields
                inspection_results = self.inspect_raw_content(file_info)
                
                if inspection_results:
                    # Add or update fields from inspection
                    
                    # Handle species name
                    if 'species_name' in inspection_results and (
                        'species_name' not in metadata or 
                        not metadata['species_name'] or
                        metadata['species_name'].strip() == ''):
                        metadata['species_name'] = inspection_results['species_name']
                        self.log(f"Added missing species name for {site_id}: {inspection_results['species_name']}", level='info')
                    
                    # Handle first_year
                    if 'first_year' in inspection_results and (
                        'first_year' not in metadata or 
                        not metadata.get('first_year')):
                        metadata['first_year'] = inspection_results['first_year']
                        self.log(f"Added/updated first_year for {site_id}: {inspection_results['first_year']}", level='info')
                    
                    # Handle last_year
                    if 'last_year' in inspection_results and (
                        'last_year' not in metadata or 
                        not metadata.get('last_year')):
                        metadata['last_year'] = inspection_results['last_year']
                        self.log(f"Added/updated last_year for {site_id}: {inspection_results['last_year']}", level='info')
                    
                    # Handle reference missing fields
                    if 'reference' in metadata:
                        ref_text = metadata['reference']
                        
                        # Add published_title if missing
                        if 'published_title' in inspection_results and 'Published_Title:' not in ref_text:
                            metadata['reference'] = ref_text + f", Published_Title: {inspection_results['published_title']}"
                            ref_text = metadata['reference']  # Update ref_text for potential pages addition
                            
                        # Add pages if missing
                        if 'pages' in inspection_results and 'Pages:' not in ref_text:
                            metadata['reference'] = ref_text + f", Pages: {inspection_results['pages']}"
        
                return metadata
            else:
                return file_info
                
        except Exception as e:
            self.log(f"Error processing {filename} from {region}: {e}", level='error')
            return file_info
    
    def process_region_files_parallel(self, region, file_list):
        """Process files from a specific region in parallel to extract metadata"""
        start_time = time.time()
        total_files = len(file_list)
        self.log(f"Starting parallel processing of {total_files} NOAA files from {region}...")
        
        # Prepare for parallel processing
        results = []
        processed_count = 0
        
        # Use larger batch size for efficiency - increased for more parallelism
        batch_size = min(400, total_files)  # Adjust based on total files
        
        # Process in batches for better memory management
        for i in range(0, total_files, batch_size):
            batch = file_list[i:i + batch_size]
            batch_start = time.time()
            batch_end = min(i + batch_size, total_files)
            self.log(f"Processing batch {i+1}-{batch_end} of {total_files} from {region}...")
            
            batch_results = []
            # Use a thread pool for I/O-bound operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Randomize the order to reduce server load on a single path
                random.shuffle(batch)
                
                # Submit all files in the batch for processing
                future_to_file = {executor.submit(self.process_file, file_info): file_info 
                                 for file_info in batch}
                
                # Process as they complete
                for future in concurrent.futures.as_completed(future_to_file):
                    processed_count += 1
                    file_info = future_to_file[future]
                    try:
                        metadata = future.result()
                        batch_results.append(metadata)
                    except Exception as e:
                        self.log(f"Error in worker processing {file_info['filename']} from {region}: {e}", level='error')
                        # Still include basic metadata even if detailed extraction failed
                        batch_results.append(file_info)
                    
                    # Log progress and save periodically
                    if processed_count % 10 == 0:
                        self.log(f"Processed {processed_count}/{total_files} files from {region} ({processed_count/total_files*100:.1f}%)")
                    
                    # Periodically save results to avoid losing progress
                    if processed_count % self.save_every == 0:
                        # Save cache to disk
                        self.save_cache(region)
            
            # Add batch results to overall results
            results.extend(batch_results)
            
            batch_time = time.time() - batch_start
            self.log(f"Completed batch {i+1}-{batch_end} from {region} in {batch_time:.2f} seconds")
            
            # Save cache after each batch
            self.save_cache(region)
        
        total_time = time.time() - start_time
        self.log(f"Completed metadata extraction for {len(results)} files from {region} in {total_time:.2f} seconds")
        if total_files > 0:
            self.log(f"Average processing time: {total_time/total_files:.4f} seconds per file")
        
        return results
    
    def validate_metadata(self, metadata_list, region=None):
        """Validate metadata and log issues before saving"""
        if not metadata_list:
            self.log(f"No metadata to validate for {region or 'global'}", level='warning')
            return metadata_list
        
        # Use a counter instead of problematic_sites list
        issue_count = 0
        
        # Check for important fields
        fields_to_check = {
            'reference': {'Published_Title': 0, 'Pages': 0},
            'species_name': 0,
            'investigators': 0
        }
        
        for metadata in metadata_list:
            has_issues = False
            
            # Check for missing or malformed fields
            for field, subfields in fields_to_check.items():
                if field not in metadata or not metadata[field]:
                    has_issues = True
                    if not isinstance(subfields, dict):
                        fields_to_check[field] += 1
                elif field == 'reference' and isinstance(subfields, dict):
                    ref_text = metadata['reference']
                    
                    for subfield in subfields:
                        exact_pattern = rf'{subfield}:\s*[^,]+'
                        if not re.search(exact_pattern, ref_text, re.IGNORECASE):
                            fields_to_check[field][subfield] += 1
                            has_issues = True
            
            if has_issues:
                issue_count += 1
        
        # Log summary of validation issues
        if issue_count > 0:
            region_info = f" in {region}" if region else ""
            self.log(f"Validation found {issue_count} sites with issues{region_info}:", level='warning')
            self.log(f"  Missing species_name: {fields_to_check['species_name']} sites", level='warning')
            self.log(f"  Missing investigators: {fields_to_check['investigators']} sites", level='warning')
            self.log(f"  Missing Published_Title: {fields_to_check['reference']['Published_Title']} sites", level='warning')
            self.log(f"  Missing Pages: {fields_to_check['reference']['Pages']} sites", level='warning')
        
        return metadata_list
    
    def fix_metadata_reference_fields(self, metadata_list, region=None):
        """Fix metadata reference fields - specifically ensuring Published_Title and Pages are present
        This is a more aggressive approach to fixing missing fields"""
        if not metadata_list:
            return metadata_list
        
        fixed_count = {'published_title': 0, 'pages': 0}
        
        for metadata in metadata_list:
            site_id = metadata.get('site_id', 'unknown')
            
            # Check if reference field exists
            if 'reference' not in metadata or not metadata['reference']:
                # Create a basic reference if none exists
                metadata['reference'] = "Authors: Unknown"
                self.log(f"Created basic reference for {site_id}", level='debug')
            
            ref_text = metadata['reference']
            
            # Check for Published_Title with proper pattern matching
            has_published_title = re.search(r'Published_Title:\s*[^,]+', ref_text, re.IGNORECASE) is not None
            if not has_published_title:
                # Generate title based on site_name or site_id
                if 'site_name' in metadata and metadata['site_name']:
                    title = f"Tree ring chronology of {metadata['site_name']}"
                else:
                    title = f"Tree ring data from site {site_id}"
                    
                ref_text = ref_text.strip() + f", Published_Title: {title}"
                fixed_count['published_title'] += 1
                self.log(f"Added synthetic title to {site_id}", level='debug')
            
            # Check for Pages with proper pattern matching
            has_pages = re.search(r'Pages:\s*[^,]+', ref_text, re.IGNORECASE) is not None
            if not has_pages:
                ref_text = ref_text.strip() + ", Pages: Data repository publication"
                fixed_count['pages'] += 1
                self.log(f"Added synthetic pages to {site_id}", level='debug')
            
            # Clean up formatting (remove double commas, etc.)
            ref_text = re.sub(r',\s*,', ',', ref_text).strip(',').strip()
            
            # Update the reference field
            metadata['reference'] = ref_text
        
        total_fixed = fixed_count['published_title'] + fixed_count['pages']
        if total_fixed > 0:
            region_info = f" for {region}" if region else ""
            self.log(f"Fixed {fixed_count['published_title']} missing Published_Title fields and {fixed_count['pages']} missing Pages fields{region_info}", level='info')
        
        return metadata_list
    
    def save_metadata(self, metadata_list, output_file, region=None, interim=False):
        """Save detailed metadata to CSV file"""
        try:
            # Skip if no metadata
            if not metadata_list:
                self.log(f"No metadata to save for {region or 'global'}", level='warning')
                return None
            
            # First validate metadata
            self.log(f"Validating metadata before saving {region or 'global'} data...", level='info')
            metadata_list = self.validate_metadata(metadata_list, region)
            
            # Fix reference fields to ensure Published_Title and Pages are present
            metadata_list = self.fix_metadata_reference_fields(metadata_list, region)
            
            # Convert metadata list to DataFrame
            df = pd.DataFrame(metadata_list)
            
            # Add source column with 'itrdb' value for all rows
            df['source'] = 'itrdb'
            
            # Clean species_name column if it exists
            if 'species_name' in df.columns:
                df['species_name'] = df['species_name'].apply(
                    lambda x: re.sub(r'^#\s*Species_Name:\s*', '', str(x)) if pd.notnull(x) else x
                )
                # Also remove standalone "#" values
                df['species_name'] = df['species_name'].apply(
                    lambda x: '' if x == '#' else x
                )
                
                # Remove Common_Name values from species_name
                df['species_name'] = df['species_name'].apply(
                    lambda x: '' if pd.notnull(x) and (str(x).startswith('Common_Name:') or 'Common_Name:' in str(x)) else x
                )
            
            # Clean common_name column if it exists
            if 'common_name' in df.columns:
                df['common_name'] = df['common_name'].apply(
                    lambda x: re.sub(r'#\s*Tree_Species_Code:\s*[\w]+', '', str(x)).strip() if pd.notnull(x) else x
                )
            
            # Clean reference column if needed
            if 'reference' in df.columns:
                # Remove any '#' markers that might appear
                df['reference'] = df['reference'].apply(
                    lambda x: re.sub(r'#\s*', '', str(x)) if pd.notnull(x) else x
                )
                # Remove any Study_Name entries
                df['reference'] = df['reference'].apply(
                    lambda x: re.sub(r'Study_Name:[^,]*,?\s*', '', str(x)).strip() if pd.notnull(x) else x
                )
                # Clean up any trailing or double commas
                df['reference'] = df['reference'].apply(
                    lambda x: re.sub(r',\s*,', ',', str(x)).strip(',').strip() if pd.notnull(x) else x
                )
                # Clean any empty values in the components
                df['reference'] = df['reference'].apply(
                    lambda x: re.sub(r'Published_Title:\s*,', '', str(x)) if pd.notnull(x) else x
                )
                df['reference'] = df['reference'].apply(
                    lambda x: re.sub(r'Pages:\s*,', '', str(x)) if pd.notnull(x) else x
                )
            
            # Remove location column if it exists
            if 'location' in df.columns:
                df = df.drop(columns=['location'])
                
            # Remove country_code column
            if 'country_code' in df.columns:
                df = df.drop(columns=['country_code'])
            
            # Set column order for better readability
            priority_columns = [
                'site_id', 'site_name', 'region', 'subdir',
                'latitude', 'longitude', 'elevation',
                'species_name', 'common_name', 'tree_species_code',
                'investigators', 'reference',
                'first_year', 'last_year',
                'filename', 'url', 'source', 'last_updated'
            ]
            
            # Reorder columns (include any new columns not in the priority list at the end)
            columns = [col for col in priority_columns if col in df.columns]
            other_columns = [col for col in df.columns if col not in priority_columns and col != 'country_code']
            final_columns = columns + other_columns
            
            # Sort data
            sort_cols = []
            if 'region' in df.columns:
                sort_cols.append('region')
            if 'subdir' in df.columns:
                sort_cols.append('subdir')
            if 'site_id' in df.columns:
                sort_cols.append('site_id')
                
            if sort_cols:
                df = df.sort_values(sort_cols)
            
            # Determine output file, create backup for interim saves
            if interim:
                output_file = f"{os.path.splitext(output_file)[0]}_interim.csv"
            
            # Check for existing file to merge with
            if os.path.exists(output_file) and not interim:
                # Create backup of existing file
                backup_file = f"{output_file}.bak"
                try:
                    self.log(f"Creating backup of existing metadata file: {backup_file}")
                    pd.read_csv(output_file).to_csv(backup_file, index=False)
                except Exception as e:
                    self.log(f"Error creating backup: {e}", level='warning')
                
                # Read existing file
                existing_df = pd.read_csv(output_file)
                existing_count = len(existing_df)
                
                self.log(f"Existing metadata file has {existing_count} entries")
                
                # Merge with existing data, keeping the new data if duplicates
                merged_df = pd.concat([existing_df, df]).drop_duplicates(subset=['site_id', 'region', 'subdir'], keep='last')
                
                # Ensure columns are ordered properly in merged data
                merged_columns = [col for col in final_columns if col in merged_df.columns]
                other_merged_columns = [col for col in merged_df.columns if col not in final_columns]
                merged_df = merged_df[merged_columns + other_merged_columns]
                
                # Sort the merged data
                if sort_cols:
                    merged_df = merged_df.sort_values(sort_cols)
                
                merged_df.to_csv(output_file, index=False)
                
                new_count = len(merged_df)
                self.log(f"Updated metadata file with {new_count - existing_count} new entries")
                self.log(f"Total sites in metadata file: {new_count}")
            else:
                # Save new metadata file with ordered columns
                if len(final_columns) > 0:
                    df = df[final_columns]
                df.to_csv(output_file, index=False)
                self.log(f"{'Interim' if interim else 'New'} metadata file created with {len(df)} entries")
            
            return output_file
        
        except Exception as e:
            self.log(f"Error saving metadata: {e}", level='error')
            import traceback
            self.log(traceback.format_exc(), level='error')
            return None
    
    def create_region_summary(self, region, output_file=None):
        """Create a summary of the metadata for a specific region"""
        if not output_file:
            if region in self.output_files:
                output_file = self.output_files[region]
            else:
                self.log(f"No output file specified for region {region}", level='error')
                return None
                
        try:
            if not os.path.exists(output_file):
                self.log(f"No metadata file found for {region} to create summary.", level='warning')
                return None
            
            # Load the metadata file
            df = pd.read_csv(output_file)
            
            # Create summary string
            summary = f"\n{region.capitalize()} Metadata Summary:\n"
            summary += f"  Total sites: {len(df)}\n"
            
            # Subdirectory breakdown for northamerica
            if 'subdir' in df.columns and not df['subdir'].isna().all():
                subdir_counts = df['subdir'].value_counts().dropna()
                if len(subdir_counts) > 0:
                    summary += f"  Subdirectories represented: {len(subdir_counts)}\n"
                    summary += "  Top 5 subdirectories by count:\n"
                    for subdir, count in subdir_counts.head(5).items():
                        summary += f"    - {subdir}: {count} sites\n"
            
            # Species counts
            if 'species_name' in df.columns and not df['species_name'].isna().all():
                species_counts = df['species_name'].value_counts().dropna()
                if len(species_counts) > 0:
                    summary += f"  Species represented: {len(species_counts)}\n"
                    summary += "  Top 5 species by count:\n"
                    for species, count in species_counts.head(5).items():
                        summary += f"    - {species}: {count} sites\n"
            
            # Time range
            if 'first_year' in df.columns and 'last_year' in df.columns:
                if not df['first_year'].isna().all() and not df['last_year'].isna().all():
                    min_year = df['first_year'].min() if not pd.isna(df['first_year'].min()) else "N/A"
                    max_year = df['last_year'].max() if not pd.isna(df['last_year'].max()) else "N/A"
                    summary += f"  Earliest year: {min_year}\n"
                    summary += f"  Latest year: {max_year}\n"
            
            # Print summary
            self.log(summary)
            
            # Save summary to file
            summary_file = os.path.join(self.metadata_dir, f"{region}_summary_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            return summary
        
        except Exception as e:
            self.log(f"Error creating summary for {region}: {e}", level='error')
            return None
    
    def create_global_summary(self):
        """Create a summary of the global metadata"""
        try:
            if not os.path.exists(self.global_output_file):
                self.log("No global metadata file found to create summary.", level='warning')
                return None
            
            # Load the global metadata file
            df = pd.read_csv(self.global_output_file)
            
            # Create summary string
            summary = "\nGlobal ITRDB Metadata Summary:\n"
            summary += f"  Total sites: {len(df)}\n"
            
            # Region counts
            if 'region' in df.columns:
                region_counts = df['region'].value_counts()
                summary += f"  Regions represented: {len(region_counts)}\n"
                summary += "  Sites per region:\n"
                for region, count in region_counts.items():
                    summary += f"    - {region}: {count} sites\n"
            
            # Species counts
            if 'species_name' in df.columns and not df['species_name'].isna().all():
                species_counts = df['species_name'].value_counts().dropna()
                if len(species_counts) > 0:
                    summary += f"  Species represented: {len(species_counts)}\n"
                    summary += "  Top 10 species by count:\n"
                    for species, count in species_counts.head(10).items():
                        summary += f"    - {species}: {count} sites\n"
            
            # Time range
            if 'first_year' in df.columns and 'last_year' in df.columns:
                if not df['first_year'].isna().all() and not df['last_year'].isna().all():
                    min_year = df['first_year'].min() if not pd.isna(df['first_year'].min()) else "N/A"
                    max_year = df['last_year'].max() if not pd.isna(df['last_year'].max()) else "N/A"
                    summary += f"  Earliest year: {min_year}\n"
                    summary += f"  Latest year: {max_year}\n"
            
            # Print summary
            self.log(summary)
            
            # Save summary to file
            summary_file = os.path.join(self.metadata_dir, f"global_summary_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            return summary
        
        except Exception as e:
            self.log(f"Error creating global summary: {e}", level='error')
            return None
    
    def run(self):
        """Run the global ITRDB metadata extraction process"""
        # Reset the start time at the beginning of the run
        self.start_time = time.time()
        
        self.log(f"Starting Global ITRDB detailed metadata extraction...")
        
        # Access the file listing for all regions
        all_files = self.get_all_files()
        
        # Process all files by region and save individual region files
        all_metadata = []
        
        for region in self.regions:
            if region not in all_files or not all_files[region]:
                self.log(f"No files found for {region}, skipping", level='warning')
                continue
                
            self.log(f"Processing {len(all_files[region])} files from {region} region...")
            
            # Process the files in parallel
            region_metadata = self.process_region_files_parallel(region, all_files[region])
            
            # Save the region metadata to its own file
            if region_metadata:
                # Save metadata for this region
                region_output_file = self.output_files[region]
                self.save_metadata(region_metadata, region_output_file, region)
                
                # Create a summary for this region
                self.create_region_summary(region, region_output_file)
                
                # Add to overall metadata
                all_metadata.extend(region_metadata)
        
        # Save the combined global metadata
        if all_metadata:
            self.log("Creating global metadata file with data from all regions...")
            self.save_metadata(all_metadata, self.global_output_file)
            
            # Create global summary
            self.create_global_summary()
        
        # Calculate total execution time
        total_time = time.time() - self.start_time
        
        # Log completion with clear separation
        self.log("-" * 60)
        self.log(f"Global metadata processing completed in {total_time:.2f} seconds")
        self.log(f"Processed {len(all_metadata)} total sites across {len(self.regions)} regions")
        self.log(f"Global metadata file: {self.global_output_file}")
        self.log("-" * 60)
        
        return True

def main():
    """Main function to parse arguments and run the global metadata extraction process"""
    try:
        parser = argparse.ArgumentParser(description='Extract detailed metadata from the ITRDB.')
        
        # Add base directory argument (not actually used directly, but keeping for consistency)
        parser.add_argument('--base-dir', dest='base_dir', type=str, default=None,
                            help='Base directory for metadata files')
        
        # Add worker count argument
        parser.add_argument('--workers', dest='workers', type=int, default=8,
                            help='Number of concurrent workers')
        
        # Add retry count argument
        parser.add_argument('--retry', dest='retry_count', type=int, default=5,
                            help='Number of retry attempts')
        
        # Add timeout argument
        parser.add_argument('--timeout', dest='timeout', type=int, default=30,
                            help='Timeout in seconds for HTTP requests')
        
        # Add progress save interval argument
        parser.add_argument('--save-every', dest='save_every', type=int, default=100,
                            help='Save progress after every N files')
        
        # Add cache control arguments
        parser.add_argument('--clear-cache', dest='clear_cache', action='store_true',
                            help='Clear the cache before starting')
        parser.add_argument('--cache-dir', dest='cache_dir', type=str, default=None,
                            help='Directory for cached data')
        
        # Add site pattern argument
        parser.add_argument('--site-pattern', dest='site_pattern', type=str, default=None,
                            help='Only process sites matching this pattern (e.g., alge001)')
        
        # Add detailed metadata option
        parser.add_argument('--skip-detailed', dest='skip_detailed', action='store_true',
                            help='Skip detailed metadata extraction')
        
        # Add region selection arguments
        parser.add_argument('--regions', dest='regions', type=str, nargs='+',
                            default=None,
                            help='Regions to process (default: all regions)')
        
        # Add output directory argument
        parser.add_argument('--output-dir', dest='output_dir', type=str, default=None,
                            help='Output directory for metadata files')
        
        # Add verbose argument
        parser.add_argument('--verbose', dest='verbose', action='store_true', default=True,
                            help='Enable verbose logging')
        
        # Add download files argument
        parser.add_argument('--download-files', dest='download_files', action='store_true',
                            help='Download .rwl files along with metadata extraction')
        
        # Parse the arguments
        args = parser.parse_args()
        
        # Print args for debugging
        print("Arguments:", args)
        
        # Set up the extractor
        extractor = GlobalDetailedMetadataFetcher(
            regions=args.regions,
            output_dir=args.output_dir,
            site_pattern=args.site_pattern,
            max_workers=args.workers,
            cache_dir=args.cache_dir,
            retry_count=args.retry_count,
            timeout=args.timeout,
            save_every=args.save_every,
            skip_detailed=args.skip_detailed,
            clear_cache=args.clear_cache,
            verbose=args.verbose,
            download_files=args.download_files
        )
        
        # Run the extraction process
        extractor.run()
        return 0
    except Exception as e:
        import traceback
        print(f"Error in main: {e}")
        print(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
