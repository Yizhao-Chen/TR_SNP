#===============================================================
#Sub-routine to select file based on user inputs
#===============================================================
import csv
#import os
#from tkinter import messagebox

def parse_range(value):
    if value == "":
        return None, None
    if ':' in value:
        start, end = map(int, value.split(':'))
        # Always ensure start <= end for consistent range comparison
        if start > end:
            start, end = end, start
        return start, end
    else:
        val = int(value)
        return val, val

def is_valid_int(value):
    try:
        # First try to convert to float (will handle both integer and decimal strings)
        float(value)
        return True
    except ValueError:
        return False

#def om(mf,year_in,year_out,reg_in,spec_in):
#def om(mf,year_in,year_out,lat_s,lat_e,lon_s,lon_e,reg_in,spec_in):
def om(mf, year_in, year_out, lat_in, lon_in, reg_in, spec_in):

    #mf = 'D:/chrome_download/Appendix S1/Cleaned datasets/itrdb-v713-cleaned-rwl/rwl_metadata.csv'
    file_list = []   #create an empty list
    #lat_s = 2500
    #lat_e = 4900
    #lon_s = -13000
    #lon_e = -7000
    

    lat_start, lat_end = parse_range(lat_in)
    lon_start, lon_end = parse_range(lon_in)
    
    # Convert year values to integers if possible
    try:
        year_in_val = int(year_in) if year_in else ""
    except ValueError:
        year_in_val = ""
    
    try:
        year_out_val = int(year_out) if year_out else ""
    except ValueError:
        year_out_val = ""
        
    with open(mf) as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Get site ID, region, and species
                id = row.get('site_id', '')
                region = row.get('region', '')
                species = row.get('tree_species_code', '')
                
                # Handle years as floats or ints
                try:
                    start = int(float(row.get('first_year', 0)))
                except (ValueError, TypeError):
                    start = 0
                    
                try:
                    end = int(float(row.get('last_year', 0)))
                except (ValueError, TypeError):
                    end = 0
                
                # Process latitude and longitude
                try:
                    # Get raw lat/lon values
                    lat_raw = row.get('latitude', '')
                    lon_raw = row.get('longitude', '')
                    
                    # Skip if missing lat/lon
                    if not lat_raw or not lon_raw:
                        continue
                    
                    # Convert to float then to integer with x100
                    lat = int(float(lat_raw) * 100)
                    lon = int(float(lon_raw) * 100)
                except (ValueError, TypeError):
                    continue
            
                # Apply filters based on the case
                if spec_in == 'all' and reg_in == 'all':
                    # Filter by year range and lat/lon
                    year_check = (not year_in_val or start <= year_in_val) and (not year_out_val or end >= year_out_val)
                    
                    # Fixed lat/lon checks
                    lat_check = lat_start is None or (lat_start <= lat <= lat_end)
                    
                    # Special handling for longitude to correctly manage negative values
                    # When dealing with negative longitudes, we need to ensure the comparisons work correctly
                    lon_check = lon_start is None or (lon_start <= lon <= lon_end)
                    
                    # Debug output for any unexpected sites
                    if id == 'wi014':
                        print(f"DEBUG - Site: {id}, Lat: {lat}, Lon: {lon}")
                        print(f"Lat range: {lat_start} to {lat_end}, Lon range: {lon_start} to {lon_end}")
                        print(f"Lat check: {lat_check}, Lon check: {lon_check}")
                    
                    if year_check and lat_check and lon_check:
                        file_list.append(id)

                elif spec_in != 'all' and reg_in == 'all':
                    # Filter by year range and species
                    if (not year_in_val or start <= year_in_val) and (not year_out_val or end >= year_out_val) and \
                    species == spec_in:
                        # Apply lat/lon filtering here too
                        lat_check = lat_start is None or (lat_start <= lat <= lat_end)
                        lon_check = lon_start is None or (lon_start <= lon <= lon_end)
                        
                        if lat_check and lon_check:
                            file_list.append(id)

                elif spec_in == 'all' and reg_in != 'all':
                    # Filter by year range and region
                    if (not year_in_val or start <= year_in_val) and (not year_out_val or end >= year_out_val) and \
                    region == reg_in:
                        # Apply lat/lon filtering here too
                        lat_check = lat_start is None or (lat_start <= lat <= lat_end)
                        lon_check = lon_start is None or (lon_start <= lon <= lon_end)
                        
                        if lat_check and lon_check:
                            file_list.append(id)

                else:
                    # Filter by year range, species, and region
                    if (not year_in_val or start <= year_in_val) and (not year_out_val or end >= year_out_val) and \
                    species == spec_in and region == reg_in:
                        # Apply lat/lon filtering here too
                        lat_check = lat_start is None or (lat_start <= lat <= lat_end)
                        lon_check = lon_start is None or (lon_start <= lon <= lon_end)
                        
                        if lat_check and lon_check:
                            file_list.append(id)
            except Exception as e:
                # Skip rows with processing errors
                print(f"Error processing row for site {row.get('site_id', 'unknown')}: {str(e)}")
                continue

    return file_list
            #else:
            #    messagebox.showerror("ERROR","No data fits")
            #    os._exit()

