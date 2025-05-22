# =====================================================================================================
# =====================================================================================================
# an interface to select tree ring data form the cleaned version of ITRDB and create a sub-dataset
# can be selected by year in this first version
# created by Yizhao Chen 2019/6/5   Win10/Python 3.7.3/Pycharm 2019.1.2
# test version update 2019/6/10
# put regions and species as options
# lat,lon options
# test version update 2019/6/14
# remove the lat,lon options temporally, need better logic representation
# link the selected dataset to a plot function
# need to put the functions into classes
# test version update 2019/6/17
# add a selection in "plot" button to plot the result from all data selected
# refine the plot scheme: add labels and legend
# test version update 2019/6/18
# output the plot data as .csv files
# add setup.py to build excutable & installation files
# give dpi to the output plot file
# test version update 2019/7/1
# add the button to plot the custmized dataset directly
# test version update 2019/12/22
# add the exact lat/lon input for global synthesis
# DBH calculation updating 2022/12
# interface updating 2022/12
# docker version set-up 2024/7
# DBH calculation updating 2024/8
# docker version updating 2024/8
# =====================================================================================================
# Docker environment variables for cache persistence:
# TR_SNP_CACHE_DIR: Set a custom location for the metadata cache
# TR_SNP_METADATA_DIR: Set a custom location for the metadata output
# TR_SNP_DATA_DIR: Set a custom location for downloaded data files
# Example docker run command with persistence:
# docker run -v /host/cache:/app/cache -e TR_SNP_CACHE_DIR=/app/cache your-tr-snp-image
# =====================================================================================================

# =====================================================================================================
# 首先设置 R 环境变量，必须在任何 rpy2 相关导入之前
# =====================================================================================================
import os
import sys

# 确保 R_HOME 设置正确
if 'R_HOME' in os.environ:
    print(f"Original R_HOME: {os.environ['R_HOME']}")
    del os.environ['R_HOME']

# 设置正确的 R_HOME
import platform
import rpy2.situation
r_home = rpy2.situation.get_r_home()
print(f"Using R at: {r_home}")
os.environ['R_HOME'] = r_home

# 设置 LD_LIBRARY_PATH
r_lib_path = os.path.join(r_home, 'lib')
if 'LD_LIBRARY_PATH' in os.environ:
    os.environ['LD_LIBRARY_PATH'] = r_lib_path + ':' + os.environ['LD_LIBRARY_PATH']
else:
    os.environ['LD_LIBRARY_PATH'] = r_lib_path

print(f"R_HOME: {os.environ['R_HOME']}")
print(f"LD_LIBRARY_PATH: {os.environ['LD_LIBRARY_PATH']}")

# Basic initialization of R - no threading protection needed at this level
# The conversion and R functions will handle their own context

# =====================================================================================================
# 导入其他非 rpy2 相关的模块
# =====================================================================================================
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import *
from shutil import copyfile
import fnmatch
import csv
import pandas as pd
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='tr_snp_app.log'
)
logger = logging.getLogger('TR_SNP')

# =====================================================================================================
# 冻结应用处理（如果需要）
# =====================================================================================================
if getattr(sys, 'frozen', False):
    # 已冻结的应用程序
    print("Running in frozen environment")
else:
    print("Running in development environment")

# =====================================================================================================
# 导入本地函数和 rpy2 相关模块
# =====================================================================================================
# 现在可以安全地导入 rpy2 相关模块
import GFNWE
import open_metafile
import plot_all_temporal
from plot_all_temporal import *
from plot_all_allometry import plot_allometry, process_tree_column
from plot_all_allometry_species import plot_allometry_species
from plot_age_only import *
import itrdb_global_detailed_metadata 
from itrdb_global_detailed_metadata import GlobalDetailedMetadataFetcher

# 导入test_allodb模块
#import test_allodb

# =====================================================================================================
# 全局变量定义
# =====================================================================================================
returnlist = []
namelist = []
global year_in
global year_out
global lat_in
global lon_in
global comboxlist
global comboxlist1
global comboxlist2
global fd
global user_selected_metadata
global source_repository_path
# Initialize global paths as empty
user_selected_metadata = ""
source_repository_path = ""

# =====================================================================================================
# 函数定义
# =====================================================================================================
# Function to handle the metadata file browse button
def browse_metadata_file():
    # Ask the user to select a metadata file
    global user_selected_metadata
    metadata_file = filedialog.askopenfilename(
        title="Select Metadata File",
        filetypes=[("CSV files", "*.csv")],
        initialdir=os.path.join(os.getcwd(), "metadata")
    )
    
    if metadata_file:
        # Update the entry field to show the selected file
        metadata_path_entry.delete(0, tk.END)
        metadata_path_entry.insert(0, metadata_file)
        
        # Store the selected file path in a global variable for later use
        user_selected_metadata = metadata_file
        print(f"Selected metadata file: {user_selected_metadata}")
        
        # Log the selection
        if 'logger' in globals():
            logger.info(f"User selected metadata file: {user_selected_metadata}")
    return

# Function to handle the source repository browse button
def browse_source_repository():
    global source_repository_path
    path = filedialog.askdirectory(title="Select the source repository")
    if path:
        source_repository_path = path
        source_path_entry.delete(0, END)
        source_path_entry.insert(0, path)
        print(f"Selected source repository: {path}")

# Function to handle the metadata button click
def fetch_metadata():
    # Check if running in Docker environment
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER')
    if in_docker:
        # Create a special dialog for Docker environment instructions
        docker_info = Toplevel(root)
        docker_info.title("Docker Environment Detected")
        docker_info.geometry('600x300')
        docker_info.transient(root)
        docker_info.grab_set()  # Make it modal
        
        # Center the dialog
        window_width = docker_info.winfo_reqwidth()
        window_height = docker_info.winfo_reqheight()
        position_right = int(root.winfo_screenwidth()/2 - window_width/2)
        position_down = int(root.winfo_screenheight()/2 - window_height/2)
        docker_info.geometry("+{}+{}".format(position_right, position_down))
        
        # Add Docker-specific information
        Label(docker_info, text="Docker Environment Detected", font=("Arial", 14, "bold")).pack(pady=10)
        
        cache_dir = os.environ.get('TR_SNP_CACHE_DIR', 'Not set - using temporary directory')
        metadata_dir = os.environ.get('TR_SNP_METADATA_DIR', 'Not set - using container directory')
        data_dir = os.environ.get('TR_SNP_DATA_DIR', 'Not set - using container directory')
        
        info_text = f"""
For data persistence in Docker, please ensure volumes are mounted correctly.
Current settings:
- Cache directory: {cache_dir}
- Metadata directory: {metadata_dir}
- Data directory: {data_dir}

Without proper volume mounts, data may be lost when the container stops.
Recommended docker run command:
docker run -v /host/cache:/app/cache -v /host/metadata:/app/metadata \\
    -e TR_SNP_CACHE_DIR=/app/cache -e TR_SNP_METADATA_DIR=/app/metadata \\
    your-tr-snp-image
        """
        
        info_label = Label(docker_info, text=info_text, justify=LEFT, padx=20, pady=10)
        info_label.pack(fill=BOTH, expand=True)
        
        Button(docker_info, text="I understand, continue", command=docker_info.destroy).pack(pady=10)
        
        # Wait for user to close the info dialog
        docker_info.wait_window()

    # Create a dialog to ask if user wants to download data as well
    download_dialog = Toplevel(root)
    download_dialog.title("Download Options")
    download_dialog.geometry('400x160')  # Made taller to accommodate more options
    download_dialog.transient(root)
    download_dialog.grab_set()  # Make it modal
    
    # Center the dialog
    window_width = download_dialog.winfo_reqwidth()
    window_height = download_dialog.winfo_reqheight()
    position_right = int(root.winfo_screenwidth()/2 - window_width/2)
    position_down = int(root.winfo_screenheight()/2 - window_height/2)
    download_dialog.geometry("+{}+{}".format(position_right, position_down))
    
    Label(download_dialog, text="Do you want to download the RWL data files as well?",
          padx=20, pady=10).pack()
    
    # Add region selection
    region_frame = Frame(download_dialog)
    region_frame.pack(pady=5)
    
    Label(region_frame, text="Select region:").pack(side=LEFT, padx=5)
    region_var = StringVar(value="northamerica")
    region_combo = ttk.Combobox(region_frame, textvariable=region_var, width=15)
    region_combo["values"] = ("all", "northamerica", "europe", "asia", "africa", "southamerica", "australia")
    region_combo.pack(side=LEFT, padx=5)
    
    download_data = BooleanVar(value=False)
    
    def start_download(download_rwl):
        selected_region = region_var.get()
        download_dialog.destroy()
        show_progress_window(download_rwl, selected_region)
    
    button_frame = Frame(download_dialog)
    button_frame.pack(pady=10)
    
    Button(button_frame, text="Yes", command=lambda: start_download(True), 
           width=10).pack(side=LEFT, padx=20)
    Button(button_frame, text="No", command=lambda: start_download(False), 
           width=10).pack(side=LEFT, padx=20)
    
    download_dialog.wait_window()

def show_progress_window(download_rwl, selected_region=None):
    # Create progress window
    progress_window = Toplevel(root)
    progress_window.title("Metadata Fetching Progress")
    progress_window.geometry('600x400')
    progress_window.transient(root)
    
    # Add a Text widget with scrollbar for logging
    frame = Frame(progress_window)
    frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    
    scrollbar = Scrollbar(frame)
    scrollbar.pack(side=RIGHT, fill=Y)
    
    log_text = Text(frame, wrap=WORD, yscrollcommand=scrollbar.set)
    log_text.pack(fill=BOTH, expand=True)
    
    scrollbar.config(command=log_text.yview)
    
    # Progress bar
    progress = ttk.Progressbar(progress_window, orient="horizontal", 
                              length=580, mode="indeterminate")
    progress.pack(padx=10, pady=10)
    progress.start()
    
    # Download counter labels
    counter_frame = Frame(progress_window)
    counter_frame.pack(fill=X, padx=10, pady=5)
    
    if download_rwl:
        download_counter = StringVar(value="0")
        Label(counter_frame, textvariable=download_counter).pack(side=LEFT, padx=5)
    
    # Current file label
    current_file_var = StringVar(value="")
    Label(progress_window, textvariable=current_file_var, anchor="w", padx=10).pack(fill=X)
    
    # Status label
    status_var = StringVar(value="Initializing...")
    status_label = Label(progress_window, textvariable=status_var, 
                         anchor="w", padx=10, pady=5)
    status_label.pack(fill=X)
    
    # Function to update the log
    def update_log(message):
        # Check if this is a download progress message
        if download_rwl and "Downloading" in message:
            # Update current file
            current_file_var.set(message.strip())
            
            # Update counter if a download completed
            if "Saved to" in message:
                try:
                    count = int(download_counter.get())
                    download_counter.set(str(count + 1))
                except ValueError:
                    pass
                
        log_text.insert(END, message + "\n")
        log_text.see(END)
        progress_window.update()
    
    # Function for actual metadata fetching in a separate thread
    def fetch_metadata_thread():
        try:
            # Select output directory
            output_dir = filedialog.askdirectory(title="Select output directory for metadata")
            if not output_dir:
                update_log("Operation cancelled.")
                progress.stop()
                status_var.set("Cancelled")
                return
            
            update_log(f"Output directory: {output_dir}")
            update_log("Starting metadata fetch...")
            update_log(f"Download files option: {download_rwl}")
            
            # Check if running in Docker and show relevant info
            in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER')
            if in_docker:
                cache_dir = os.environ.get('TR_SNP_CACHE_DIR', 'Not set - using temporary directory')
                metadata_dir = os.environ.get('TR_SNP_METADATA_DIR', 'Not set - using container directory')
                data_dir = os.environ.get('TR_SNP_DATA_DIR', 'Not set - using container directory')
                
                update_log("\n=== Docker Environment Detected ===")
                update_log(f"Cache directory: {cache_dir}")
                update_log(f"Metadata directory: {metadata_dir}")
                update_log(f"Data directory: {data_dir}")
                update_log("Note: Without proper volume mounts, data may be lost when container stops")
                update_log("===============================\n")
            
            # Custom logger function to capture output to our window
            def custom_logger(message, level='info'):
                update_log(message)
            
            # Create a wrapper for download_rwl_file to track progress
            if download_rwl:
                # Get reference to original method
                original_download_method = GlobalDetailedMetadataFetcher.download_rwl_file
                # Total files counter for progress reporting
                download_total = [0]
                download_success = [0]
                
                # Create a wrapper function
                def download_with_progress(self, file_info):
                    # Update counters
                    download_total[0] += 1
                    # Show detailed download information
                    file_name = file_info.get('filename', 'unknown')
                    file_url = file_info.get('url', 'unknown')
                    update_log(f"Downloading file {download_total[0]}: {file_name}")
                    update_log(f"URL: {file_url}")
                    
                    # Get the target file path to check if download succeeded
                    site_id = file_info.get('site_id', 'unknown')
                    region = file_info.get('region', 'unknown')
                    subdir = file_info.get('subdir')
                    
                    # Create target path like the original method does
                    region_dir = os.path.join(self.data_dir, region)
                    if subdir:
                        region_dir = os.path.join(region_dir, subdir)
                    target_file = os.path.join(region_dir, f"{site_id}.rwl")
                    
                    # Check if file already exists (success by definition)
                    file_existed = os.path.exists(target_file)
                    
                    # Call original method
                    original_download_method(self, file_info)
                    
                    # Check if file now exists
                    download_succeeded = os.path.exists(target_file)
                    
                    if file_existed:
                        update_log(f"File already exists: {target_file}")
                        # Only count as success if it wasn't already there
                        download_success[0] += 0
                    elif download_succeeded:
                        download_success[0] += 1
                        update_log(f"Downloaded successfully: {file_name}")
                    else:
                        update_log(f"Failed to download: {file_name}")
                    
                    update_log(f"Progress: {download_success[0]}/{download_total[0]} files")
                
                # Replace the method in the class
                GlobalDetailedMetadataFetcher.download_rwl_file = download_with_progress
            
            # Initialize the metadata fetcher with our custom logger
            fetcher = GlobalDetailedMetadataFetcher(
                output_dir=output_dir,
                download_files=download_rwl,
                verbose=True,
                regions=None if selected_region == "all" else [selected_region]
            )
            
            # Add debug information to verify settings
            update_log(f"Debug: Download files parameter set to: {download_rwl}")
            update_log(f"Debug: Fetcher download_files attribute: {fetcher.download_files}")
            update_log(f"Debug: Selected region: {selected_region if selected_region != 'all' else 'ALL REGIONS'}")
            update_log(f"Debug: Cache directory: {fetcher.cache_dir}")
            update_log(f"Debug: Data directory: {fetcher.data_dir}")
            
            # Add a direct test of the download system on a known file
            if download_rwl and selected_region and selected_region != "all":
                update_log(f"\n=== Testing direct download of a sample file ===")
                # Create a test file_info object for a known sample in the selected region
                # Samples for each region:
                region_samples = {
                    'africa': {'site_id': 'zime001', 'region': 'africa', 'filename': 'zime001.rwl'},
                    'asia': {'site_id': 'mong001', 'region': 'asia', 'filename': 'mong001.rwl'},
                    'australia': {'site_id': 'tasm001', 'region': 'australia', 'filename': 'tasm001.rwl'},
                    'europe': {'site_id': 'spai001', 'region': 'europe', 'filename': 'spai001.rwl'},
                    'northamerica': {'site_id': 'ca001', 'region': 'northamerica', 'filename': 'ca001.rwl'},
                    'southamerica': {'site_id': 'arge001', 'region': 'southamerica', 'filename': 'arge001.rwl'}
                }
                
                # Get sample for selected region
                sample = region_samples.get(selected_region)
                if sample:
                    try:
                        # Construct full URL for the file
                        base_url = fetcher.base_url + selected_region + "/"
                        sample['standard_url'] = base_url + sample['filename'] 
                        sample['url'] = base_url + sample['filename'] + '-noaa.rwl'  # Add NOAA suffix for metadata
                        
                        # Directly test downloading this file
                        update_log(f"Testing direct download of {sample['filename']} from {selected_region}")
                        fetcher.download_rwl_file(sample)
                        
                        # Check if file was downloaded
                        site_id = sample['site_id']
                        region_dir = os.path.join(fetcher.data_dir, selected_region)
                        target_file = os.path.join(region_dir, f"{site_id}.rwl")
                        
                        if os.path.exists(target_file):
                            update_log(f"Test download successful! File saved to: {target_file}")
                        else:
                            update_log(f"Test download failed. File not found at: {target_file}")
                    except Exception as e:
                        update_log(f"Test download error: {str(e)}")
                else:
                    update_log(f"No sample data available for region: {selected_region}")
            
            # Explicitly force the download_files parameter to True if needed
            if download_rwl:
                fetcher.download_files = True
                update_log(f"Debug: Explicitly set download_files to True")
            
            # Replace the log method to use our UI
            fetcher.log = custom_logger
            
            # Run the fetcher
            status_var.set("Fetching metadata...")
            
            # Check if the download_rwl_file method exists
            if hasattr(fetcher, 'download_rwl_file'):
                update_log(f"Debug: download_rwl_file method found")
            else:
                update_log(f"Debug: WARNING - download_rwl_file method NOT found!")
                
            # Check if process_file method exists and handles downloads
            if hasattr(fetcher, 'process_file'):
                update_log(f"Debug: process_file method found")
                # Peek at the method to see if it handles downloads
                import inspect
                process_file_code = inspect.getsource(fetcher.process_file)
                if "download" in process_file_code.lower():
                    update_log(f"Debug: process_file method appears to handle downloads")
                else:
                    update_log(f"Debug: process_file method may NOT handle downloads")
            
            fetcher.run()
            
            # When done
            progress.stop()
            status_var.set("Done!")
            
            # Show download summary if applicable
            if download_rwl and download_total[0] > 0:
                update_log(f"\n=== Download Summary ===")
                update_log(f"Total files processed: {download_total[0]}")
                update_log(f"Successfully downloaded: {download_success[0]}")
                update_log(f"Failed downloads: {download_total[0] - download_success[0]}")
            
            update_log("\n=== Process completed successfully ===")
            
            # For Docker, add a reminder about data persistence
            if in_docker:
                update_log("\n=== Docker Environment Note ===")
                update_log("Remember that data in non-mounted volumes will be lost when the container stops")
                update_log(f"Cache directory: {fetcher.cache_dir}")
                update_log(f"Data directory: {fetcher.data_dir}")
            
            # Add a close button
            Button(progress_window, text="Close", command=progress_window.destroy).pack(pady=10)
            
            # Restore original method
            if download_rwl:
                GlobalDetailedMetadataFetcher.download_rwl_file = original_download_method
            
        except Exception as e:
            update_log(f"Error: {str(e)}")
            progress.stop()
            status_var.set("Error occurred")
            
            # Add a close button even on error
            Button(progress_window, text="Close", command=progress_window.destroy).pack(pady=10)
            
            # Make sure to restore original method in case of error
            if download_rwl:
                try:
                    GlobalDetailedMetadataFetcher.download_rwl_file = original_download_method
                except:
                    pass
    
    # Start the process in a separate thread to keep UI responsive
    import threading
    thread = threading.Thread(target=fetch_metadata_thread)
    thread.daemon = True
    thread.start()

def metafile():  # read the metafile
    year_in = entry.get()
    year_out = entry1.get()
    lat_in = entry2.get()
    lon_in = entry3.get()
    # lat_s = entry2.get()
    # lat_e = entry3.get()
    # lon_s = entry4.get()
    # lon_e = entry5.get()
    reg_in = comboxlist1.get()
    spec_in = comboxlist.get()
    print(reg_in)

    filetypes = [("*metadata.csv files", "*.csv")]
    mf = filedialog.askopenfilename(filetypes=filetypes)
    if mf == "":
        messagebox.showerror("error", "plz select the metafile")
        return
    
    #folder_path = os.path.dirname(mf)

    # namelist = open_metafile.om(mf, year_in, year_out, reg_in,spec_in)
    # namelist = open_metafile.om(mf,year_in,year_out,lat_s,lat_e,lon_s,lon_e,reg_in,spec_in)
    namelist = open_metafile.om(mf, year_in, year_out, lat_in, lon_in, reg_in, spec_in)
    print("namelist = ")
    print(namelist)
    # print(year_in)
    # print(year_out)
    # print(spec_in)
    return namelist


def select_folder():
    fd = filedialog.askdirectory()
    print(fd)
    return fd


# def select_region():
def search_create():
    global user_selected_metadata
    global source_repository_path
    
    # Get metadata path from entry field
    metadata_file = metadata_path_entry.get()
    if not metadata_file:
        messagebox.showerror("Error", "Please select a metadata file")
        return
    
    # Get source repository path from entry field
    path = source_path_entry.get()
    if not path:
        messagebox.showerror("Error", "Please select the source repository")
        return
    
    # Store metadata file globally for later use
    user_selected_metadata = metadata_file
    source_repository_path = path
    
    # Continue with existing functionality
    returnlist = open_metafile.om(metadata_file, entry.get(), entry1.get(), entry2.get(), entry3.get(), 
                               comboxlist1.get(), comboxlist.get())
    if returnlist == []:  # no matched data
        messagebox.showerror("Error", "No data fits the criteria")
        return
        
    # Select output repository directly
    fd = filedialog.askdirectory(title="Select repository for output")
    if fd == "":
        messagebox.showerror("Error", "Please select repository for output")
        return

    file_path = os.path.join(fd, "sub_log.txt")
    with open(file_path, 'w') as f:
        for i in range(0, len(returnlist)):
            f.write(str(returnlist[i]))
            f.write('\n')
    
    # Use the previously selected source repository path
    path_list = os.walk(path)
    output_fl = []
    output_fn = []
    for root, dirs, files in path_list:
        flength = len(files)
        for i in range(0, flength):
            fname = GFNWE.getFileNameWithoutExtension(files[i])
            fname1 = None
            if fname in returnlist:
                fname1 = files[i]
                destination_path = os.path.join(fd, fname1)
                if not os.path.exists(destination_path):
                    copyfile(os.path.join(root, fname1), destination_path)
                output_fl.append(destination_path)
                output_fn.append(fname1)
                print(fname1)  # the select files
    plot_R(output_fl, output_fn)


def plot_R(output_fl, output_fn):
    print(f"output_fl: {output_fl}")
    print(f"output_fn: {output_fn}")
    if not output_fl:
        messagebox.showerror("error", "plz select the target repository")
        return
    
    # Store the output directory for later use
    # Extract the directory from the first file path
    output_dir = os.path.dirname(output_fl[0])
    
    # Find the position of search_create button to position plot button below it
    search_create_btn_info = search_create_button.grid_info()
    row_position = search_create_btn_info['row']
    col_position = search_create_btn_info['column']
    
    # Position plot button directly below search_create button
    plot_button = Button(root, text='process', command=lambda: on_click(output_dir))
    plot_button.grid(row=row_position+1, column=col_position, pady=5)


def on_click(output_dir):
    """
    Open a file selection dialog allowing the user to select multiple files
    from the previously selected output directory.
    """
    # Open file selection dialog with initial directory set to output_dir
    selected_files = filedialog.askopenfilenames(
        title="Select files to process",
        initialdir=output_dir,
        filetypes=[("Tree ring files", "*.rwl"), ("All files", "*.*")]
    )
    
    if not selected_files:
        messagebox.showinfo("Information", "No files selected")
        return
        
    # Convert selected files to a list
    selected_files_list = list(selected_files)
    
    # Get just the filenames without paths for display purposes
    selected_filenames = [os.path.basename(file) for file in selected_files_list]
    
    # Call plot_all_ometry with the selected files
    plot_all_ometry(selected_files_list, 0)  # 0 indicates all files as a group

def plot_all_ometry(output_fl,nIndex):
    fk = []
    if nIndex == 0:
        fk = output_fl
    else:
        fk = [output_fl[nIndex - 1]]

    print(f"fk: {fk}")
    print(f"fk[0]: {fk[0]}")
    configuration_dialog(fk)

#1、通过用户file_select的文件的名称，是否在数据库rwl_metadata_2020_4_18_all_nontrw_non_species_removed_to_shp 中做分支判断
#2、如果不在文件中，则让用户再次选region和species，传递到allometric_dict.py中 用来判断算法的选择，代替原本用文件名称判断方式
# a temporal module to plot the customized tree ring data directly
# add BAI(basal area increment) plot Yizhao 2019/7/10
def file_select():
    # Get file selection from user - removed dependency on rwl_metadata_ITRDB.csv
    fk = filedialog.askopenfilenames(title="select TR files")
    print(fk)
    
    if fk:
        # Always use manual region/species selection when using file_select
        configuration_dialog(fk, file_names_in_csv=False)

def configuration_dialog(fk, file_names_in_csv=True):
    # Initialize file_Column_Randoms for each file
    file_Column_Randoms = [[0] * len(r['read.tucson'](file_path).colnames) for file_path in fk]
    
    # Initialize dictionaries for geometric and bark correction rates
    geometric_correction_rates = [{} for _ in fk]
    bark_correction_rates = [{} for _ in fk]
    
    # Default rates if no custom values are provided
    default_geometric_rate = 1.0
    default_bark_rate = 0.05
    
    # Use the global metadata file if available (from search_create), otherwise use empty string
    metadata_file = user_selected_metadata if 'user_selected_metadata' in globals() and file_names_in_csv else "metadata.csv"
    
    # Define the apply_correction function first, before it's referenced
    def apply_correction():        
        #定义三个变量分别存储随机模式时候的最大随机值、最小随机值、随机次数
        max_value = 0
        min_value = 0
        times = 0

        if var_correction.get() == 1:
            print("Mean")
        elif var_correction.get() == 3:
            # 随机值
            try:
                min_value = float(entry_min.get())
                max_value = float(entry_max.get())
                times = int(entry_time.get())
                if(0 >= times):
                    messagebox.showerror("Invalid Input", "Please enter valid numbers.")
                    return
                if min_value < max_value:
                    print(f"min_value: {min_value}")
                else:
                    messagebox.showerror("Invalid Range", "Min value should be less than Max value.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers.")
                return
        elif var_correction.get() == 2:
            times = -1
        else:
            print("None")

        # Handle DBH calculation method
        dbh_method = var_dbh.get()
        # Adjust the dbh_method value for compatibility with the processing functions
        # Now: 0=No, 1=Lockwood, 2=Customize
        # The processing functions expect: 0=Lockwood, 1=Other/Customize
        if dbh_method == 0:  # "No" option
            dbh_method = -1  # Use a special value to indicate no correction
        elif dbh_method == 1:  # "Lockwood" option
            dbh_method = 0   # The value expected by processing functions
        elif dbh_method == 2:  # "Customize" option
            dbh_method = 1   # The value expected by processing functions
        
        # Handle Bark method
        bark_method = var_bark.get()
        # Now: 0=No, 1=Yes, 2=Customize
        if bark_method == 2:  # "Customize" option
            bark_method = -1  # Special value for customization
        
        # Handle file output path
        output_path = entry_output_path.get()
        
        # Use metadata_file from parent scope
        print(f"Using metadata file: {metadata_file}")
        
        print(f"min_max_times:", min_value,max_value,times)

        # Check if params file is required and selected
        if not file_names_in_csv:
            # Check if parameters file is selected
            if not hasattr(select_params_file, 'site_ids'):
                messagebox.showerror("Error", "Please select a site parameters file first")
                return
                
            # Check if parameter list lengths match file count
            if len(select_params_file.site_ids) != len(fk):
                messagebox.showerror("Error", 
                    f"Number of parameter sets ({len(select_params_file.site_ids)}) " +
                    f"does not match number of files ({len(fk)})")
                return
        
        # Modify how plot_allometry_species is called
        if file_names_in_csv:
            try:
                # Pass geometric_correction_rates and bark_correction_rates
                plot_allometry(fk, min_value, max_value, times, file_Column_Randoms, 
                               dbh_method, bark_method, output_path, metadata_file,
                               geometric_correction_rates=geometric_correction_rates,
                               bark_correction_rates=bark_correction_rates)
            except Exception as e:
                error_msg = f"Error processing files: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Processing Error", f"An error occurred while processing files:\n{str(e)}\n\nCheck the log for details.")
                return
        else:
            # Use parameter lists to call processing function
            try:
                # Ensure all lists have the same length
                if not (len(fk) == len(select_params_file.site_ids) == len(select_params_file.regionls) == 
                        len(select_params_file.speciesls) == len(select_params_file.latls) == len(select_params_file.lonls)):
                    raise ValueError("Mismatch between number of files and parameter sets")
                
                # Import threading protection for rpy2
                # Since we can't rely on specific initialization methods,
                # we'll use simpler techniques and rely on conversion contexts
                
                # Process files one by one with proper error handling
                plot_allometry_species(
                    fk,
                    min_value,
                    max_value,
                    times,
                    file_Column_Randoms,
                    dbh_method,
                    bark_method,
                    output_path,
                    select_params_file.site_ids,
                    select_params_file.regionls,
                    select_params_file.speciesls,
                    select_params_file.latls,
                    select_params_file.lonls,
                    geometric_correction_rates,
                    bark_correction_rates
                )
            except Exception as e:
                error_msg = f"Error processing files: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Processing Error", f"An error occurred while processing files:\n{str(e)}\n\nCheck the log for details.")
                return
            
        dialog.destroy()

    def select_csv(file_path, idx, correction_type='initial'):
        csv_path = filedialog.askopenfilename(title=f"Select CSV for {os.path.basename(file_path)}", 
                                            filetypes=[("CSV files", "*.csv")])
        if csv_path:
            try:
                # Try different encodings
                try:
                    # Try utf-8 first
                    csv_df = pd.read_csv(csv_path, encoding='utf-8')
                    logger.info(f"Successfully read CSV with UTF-8 encoding")
                except UnicodeDecodeError:
                    # Fall back to other encodings
                    try:
                        csv_df = pd.read_csv(csv_path, encoding='latin1')
                        logger.info(f"Successfully read CSV with latin1 encoding")
                    except:
                        csv_df = pd.read_csv(csv_path, encoding='cp1252')
                        logger.info(f"Successfully read CSV with cp1252 encoding")
                
                # Clean up sample names by stripping whitespace
                if 'sample' in csv_df.columns:
                    csv_df['sample'] = csv_df['sample'].str.strip()
                    logger.info(f"Cleaned sample names by stripping whitespace")
                    
                # Dump exact sample names for debugging
                if 'sample' in csv_df.columns:
                    logger.info(f"CSV sample names: {[repr(name) for name in csv_df['sample'][:10]]}")
                
                # Check if the file has the expected format with sample names
                if 'sample' in csv_df.columns:
                    logger.info("CSV file contains 'sample' column")
                    # Determine the value column based on correction type
                    value_col = None
                    if correction_type == 'geometric' and 'geometric_rate' in csv_df.columns:
                        value_col = 'geometric_rate'
                        logger.info(f"Using '{value_col}' column for geometric correction rates")
                    elif correction_type == 'bark' and 'bark_rate' in csv_df.columns:
                        value_col = 'bark_rate'
                        logger.info(f"Using '{value_col}' column for bark correction rates")
                    elif correction_type == 'initial' and any(col.startswith('initbias') for col in csv_df.columns):
                        # Find the initial bias column (might have different names like "initbias 0.1mm")
                        value_col = next((col for col in csv_df.columns if col.startswith('initbias')), None)
                        logger.info(f"Using '{value_col}' column for initial width bias")
                    
                    if value_col:
                        # Get the tree sample names from the file being processed
                        rwl_data = r['read.tucson'](file_path)
                        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
                            tree_names = list(rwl_data.colnames)
                        
                        logger.info(f"Tree ring file sample names: {tree_names}")
                        
                        # Create a dictionary mapping sample names to correction values
                        correction_dict = dict(zip(csv_df['sample'], csv_df[value_col]))
                        logger.info(f"Correction dictionary keys: {list(correction_dict.keys())}")
                        logger.info(f"First few values: {dict(list(correction_dict.items())[:5])}")
                        
                        # Verify sample name matching
                        matches = [name for name in tree_names if name in correction_dict]
                        logger.info(f"Found {len(matches)} matches between tree samples and CSV samples")
                        if not matches and len(tree_names) > 0 and len(correction_dict) > 0:
                            logger.warning("WARNING: No matching sample names found between tree ring file and CSV!")
                        
                        # Store the correction dictionary directly for geometric and bark corrections
                        if correction_type == 'geometric':
                            geometric_correction_rates[idx] = correction_dict
                            logger.info(f"Loaded geometric correction rates for {len(correction_dict)} samples")
                        elif correction_type == 'bark':
                            bark_correction_rates[idx] = correction_dict
                            logger.info(f"Loaded bark correction rates for {len(correction_dict)} samples")
                        else:
                            # For initial width, keep the original list approach
                            correction_values = []
                            for tree_name in tree_names:
                                # If tree name exists in the CSV, use its value, otherwise use default (0)
                                correction_values.append(correction_dict.get(tree_name, 0))
                            file_Column_Randoms[idx] = correction_values
                        
                        messagebox.showinfo("Success", f"Loaded {len(correction_dict)} sample-specific {correction_type} correction values")
                    else:
                        # Fallback to original behavior if the expected value column isn't found
                        logger.warning(f"No '{correction_type}_rate' column found in CSV file")
                        values = csv_df.iloc[:, 1].tolist()  # Use second column instead of first
                        logger.info(f"Using column index 1 values as fallback: {values[:5]}...")
                        if correction_type == 'geometric':
                            # Convert to dictionary with sequential keys for backward compatibility
                            geometric_correction_rates[idx] = dict(zip(range(len(values)), values))
                        elif correction_type == 'bark':
                            # Convert to dictionary with sequential keys for backward compatibility
                            bark_correction_rates[idx] = dict(zip(range(len(values)), values))
                        else:
                            file_Column_Randoms[idx] = values
                        messagebox.showinfo("Success", f"Loaded {len(values)} values from {os.path.basename(csv_path)}")
                else:
                    # Fallback to original behavior for files without the expected format
                    logger.warning("CSV file does not contain 'sample' column")
                    values = csv_df.iloc[:, 0].tolist()
                    logger.info(f"Using column index 0 values as fallback: {values[:5]}...")
                    if correction_type == 'geometric':
                        # Convert to dictionary with sequential keys for backward compatibility
                        geometric_correction_rates[idx] = dict(zip(range(len(values)), values))
                    elif correction_type == 'bark':
                        # Convert to dictionary with sequential keys for backward compatibility
                        bark_correction_rates[idx] = dict(zip(range(len(values)), values))
                    else:
                        file_Column_Randoms[idx] = values
                    messagebox.showinfo("Success", f"Loaded {len(values)} values from {os.path.basename(csv_path)}")
            except Exception as e:
                error_msg = f"Failed to load CSV: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)

    def select_params_file():
        csv_file = filedialog.askopenfilename(
            title="Select Site Parameters File",
            filetypes=[("CSV files", "*.csv")],
            initialdir=os.getcwd()
        )
        if csv_file:
            try:
                # Read the CSV file
                params_df = pd.read_csv(csv_file)
                
                # Validate file format
                required_columns = ['site_id', 'region', 'species', 'latitude', 'longitude']
                if not all(col in params_df.columns for col in required_columns):
                    messagebox.showerror("Error", 
                        "CSV file must contain columns: site_id, region, species, latitude, longitude")
                    return
                
                # Validate data types
                try:
                    params_df['latitude'] = params_df['latitude'].astype(float)
                    params_df['longitude'] = params_df['longitude'].astype(float)
                except ValueError:
                    messagebox.showerror("Error", "Latitude and longitude must be numeric values")
                    return
                
                # Display file path and number of parameter sets
                file_label.config(text=f"{os.path.basename(csv_file)} ({len(params_df)} sets)")
                
                # Store parameter lists
                select_params_file.site_ids = params_df['site_id'].tolist()
                select_params_file.regionls = params_df['region'].tolist()
                select_params_file.speciesls = params_df['species'].tolist()
                select_params_file.latls = params_df['latitude'].tolist()
                select_params_file.lonls = params_df['longitude'].tolist()
                
            except Exception as e:
                messagebox.showerror("Error", f"Error reading CSV file: {str(e)}")
                return

    def update_ui():
        # Handle Initial Width Correction
        if var_correction.get() == 1:
            entry_frame.grid_remove()
            random_frame.grid_remove()
        elif var_correction.get() == 2:
            entry_frame.grid()
            random_frame.grid_remove()
        elif var_correction.get() == 3:
            entry_frame.grid_remove()
            random_frame.grid()
            
        # Handle Geometric Correction
        if var_dbh.get() == 2:  # Customize
            geometric_frame.grid()
        else:
            geometric_frame.grid_remove()
            
        # Handle Bark Width Correction
        if var_bark.get() == 2:  # Customize
            bark_frame.grid()
        else:
            bark_frame.grid_remove()

    def select_output_path():
        path = filedialog.askdirectory(title="Select Output Path")
        if path:
            entry_output_path.delete(0, tk.END)
            entry_output_path.insert(0, path)

    def show_samples(file_path):
        # 使用 rpy2 读取文件并获取列名
        TR_input = r['read.tucson'](file_path)
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            pdf_input = pandas2ri.rpy2py(TR_input)
        
        # 创建弹出框显示列名
        sample_dialog = tk.Toplevel(dialog)
        sample_dialog.title("Samples Names")
        sample_dialog.geometry('500x600')
        
        # 使用 Canvas 和 Scrollbar 显示列名
        canvas = tk.Canvas(sample_dialog)
        scrollbar = ttk.Scrollbar(sample_dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 显示列名
        for col_name in pdf_input.columns:
            tk.Label(scrollable_frame, text=col_name).pack()
            print(f"{col_name}")

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    dialog = tk.Toplevel(root)
    dialog.title("Configuration")
    dialog.geometry('1200x600')
    dialog.transient(root)  # Make the dialog appear above the root window

    # Configure grid columns and rows to have equal weight
    for i in range(2):
        dialog.grid_columnconfigure(i, weight=1, minsize=300)
    for i in range(4):
        dialog.grid_rowconfigure(i, weight=1)

    # Initial Width Bias Correction Group Box
    group_box_correction = tk.LabelFrame(dialog, text="Initial Width Correction")
    group_box_correction.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    var_correction = tk.IntVar(value=1)
    tk.Radiobutton(group_box_correction, text="No", variable=var_correction, value=1, command=update_ui).grid(row=0, column=0, padx=10, pady=5)
    tk.Radiobutton(group_box_correction, text="Customize", variable=var_correction, value=2, command=update_ui).grid(row=0, column=1, padx=10, pady=5)
    tk.Radiobutton(group_box_correction, text="Random", variable=var_correction, value=3, command=update_ui).grid(row=0, column=2, padx=10, pady=5)

    entry_frame = tk.Frame(group_box_correction)
    entry_frame.grid(row=1, column=0, columnspan=3, pady=5)
    entry_frame.grid_remove()

    # Add a scrollbar to the entry_frame
    canvas = tk.Canvas(entry_frame)
    scrollbar = ttk.Scrollbar(entry_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # 修改 entry_frame 为每个文件创建一行
    for index, file_path in enumerate(fk):
        file_frame = tk.Frame(scrollable_frame)
        file_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Label(file_frame, text=os.path.basename(file_path)).pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="Show samples", command=lambda fp=file_path: show_samples(fp)).pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="File selection", command=lambda fp=file_path, idx=index: select_csv(fp, idx)).pack(side=tk.LEFT, padx=5)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    random_frame = tk.Frame(group_box_correction)
    random_frame.grid(row=1, column=0, columnspan=3, pady=5)
    random_frame.grid_remove()
    tk.Label(random_frame, text="Min:").pack(side=tk.LEFT, padx=5)
    entry_min = tk.Entry(random_frame, width=10)
    entry_min.pack(side=tk.LEFT, padx=5)
    tk.Label(random_frame, text="Max:").pack(side=tk.LEFT, padx=5)
    entry_max = tk.Entry(random_frame, width=10)
    entry_max.pack(side=tk.LEFT, padx=5)
    tk.Label(random_frame, text="Times:").pack(side=tk.LEFT, padx=5)
    entry_time = tk.Entry(random_frame, width=10)
    entry_time.pack(side=tk.LEFT, padx=5)

    # Geometric Correction Group Box
    group_box_dbh = tk.LabelFrame(dialog, text="Geometric Correction")
    group_box_dbh.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    var_dbh = tk.IntVar(value=0)
    tk.Radiobutton(group_box_dbh, text="No", variable=var_dbh, value=0, command=update_ui).grid(row=0, column=0, padx=10, pady=5)
    tk.Radiobutton(group_box_dbh, text="Lockwood", variable=var_dbh, value=1, command=update_ui).grid(row=0, column=1, padx=10, pady=5)
    tk.Radiobutton(group_box_dbh, text="Customize", variable=var_dbh, value=2, command=update_ui).grid(row=0, column=2, padx=10, pady=5)

    # Add a frame for geometric correction customization
    geometric_frame = tk.Frame(group_box_dbh)
    geometric_frame.grid(row=1, column=0, columnspan=3, pady=5)
    geometric_frame.grid_remove()
    
    # Add a scrollbar to the geometric_frame
    geometric_canvas = tk.Canvas(geometric_frame)
    geometric_scrollbar = ttk.Scrollbar(geometric_frame, orient="vertical", command=geometric_canvas.yview)
    geometric_scrollable_frame = ttk.Frame(geometric_canvas)

    geometric_scrollable_frame.bind(
        "<Configure>",
        lambda e: geometric_canvas.configure(
            scrollregion=geometric_canvas.bbox("all")
        )
    )

    geometric_canvas.create_window((0, 0), window=geometric_scrollable_frame, anchor="nw")
    geometric_canvas.configure(yscrollcommand=geometric_scrollbar.set)

    # Add file rows to geometric_frame
    for index, file_path in enumerate(fk):
        geo_file_frame = tk.Frame(geometric_scrollable_frame)
        geo_file_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Label(geo_file_frame, text=os.path.basename(file_path)).pack(side=tk.LEFT, padx=5)
        tk.Button(geo_file_frame, text="Show samples", command=lambda fp=file_path: show_samples(fp)).pack(side=tk.LEFT, padx=5)
        tk.Button(geo_file_frame, text="File selection", command=lambda fp=file_path, idx=index: select_csv(fp, idx, 'geometric')).pack(side=tk.LEFT, padx=5)

    geometric_canvas.pack(side="left", fill="both", expand=True)
    geometric_scrollbar.pack(side="right", fill="y")

    # Bark correction Group Box
    group_box_bark = tk.LabelFrame(dialog, text="Bark Width Correction")
    group_box_bark.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    var_bark = tk.IntVar(value=0)
    tk.Radiobutton(group_box_bark, text="No", variable=var_bark, value=0, command=update_ui).grid(row=0, column=0, padx=10, pady=5)
    tk.Radiobutton(group_box_bark, text="Allometry", variable=var_bark, value=1, command=update_ui).grid(row=0, column=1, padx=10, pady=5)
    tk.Radiobutton(group_box_bark, text="Customize", variable=var_bark, value=2, command=update_ui).grid(row=0, column=2, padx=10, pady=5)
    
    # Add a frame for bark correction customization
    bark_frame = tk.Frame(group_box_bark)
    bark_frame.grid(row=1, column=0, columnspan=3, pady=5)
    bark_frame.grid_remove()
    
    # Add a scrollbar to the bark_frame
    bark_canvas = tk.Canvas(bark_frame)
    bark_scrollbar = ttk.Scrollbar(bark_frame, orient="vertical", command=bark_canvas.yview)
    bark_scrollable_frame = ttk.Frame(bark_canvas)

    bark_scrollable_frame.bind(
        "<Configure>",
        lambda e: bark_canvas.configure(
            scrollregion=bark_canvas.bbox("all")
        )
    )

    bark_canvas.create_window((0, 0), window=bark_scrollable_frame, anchor="nw")
    bark_canvas.configure(yscrollcommand=bark_scrollbar.set)

    # Add file rows to bark_frame
    for index, file_path in enumerate(fk):
        bark_file_frame = tk.Frame(bark_scrollable_frame)
        bark_file_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        tk.Label(bark_file_frame, text=os.path.basename(file_path)).pack(side=tk.LEFT, padx=5)
        tk.Button(bark_file_frame, text="Show samples", command=lambda fp=file_path: show_samples(fp)).pack(side=tk.LEFT, padx=5)
        tk.Button(bark_file_frame, text="File selection", command=lambda fp=file_path, idx=index: select_csv(fp, idx, 'bark')).pack(side=tk.LEFT, padx=5)

    bark_canvas.pack(side="left", fill="both", expand=True)
    bark_scrollbar.pack(side="right", fill="y")

    # Replace Region and Species section with Site Parameters File section
    group_box_site_params = tk.LabelFrame(dialog, text="Site Parameters File")
    group_box_site_params.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    # Add file selection button and label
    select_button = tk.Button(group_box_site_params, text="Select Parameters File", command=select_params_file)
    select_button.grid(row=0, column=0, padx=10, pady=10)
    
    file_label = tk.Label(group_box_site_params, text="No file selected")
    file_label.grid(row=0, column=1, padx=10, pady=10)
    
    # Initialize file path storage
    select_params_file.filepath = None

    # Set column weights for even distribution
    group_box_site_params.grid_columnconfigure(1, weight=1)

    # Show or hide the site parameters group box based on file_names_in_csv
    if file_names_in_csv:
        group_box_site_params.grid_remove()
    else:
        group_box_site_params.grid()

    # Select File Output Path Group Box
    group_box_output = tk.LabelFrame(dialog, text="Select File Output Path")
    group_box_output.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

    entry_output_path = tk.Entry(group_box_output)
    entry_output_path.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    entry_output_path.insert(0, os.getcwd())  # Default to current working directory
    tk.Button(group_box_output, text="Select", command=select_output_path).grid(row=0, column=1, padx=10, pady=5)

    group_box_output.grid_columnconfigure(0, weight=1)

    # Apply Button - ensure it's properly positioned
    apply_button = tk.Button(dialog, text="Apply", command=apply_correction, width=20)
    apply_button.grid(row=3, column=0, columnspan=2, pady=20, padx=10, sticky="se")
    
    # Set column weights for proper layout
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=1)

# interface design
root = Tk()
root.title('TR_SNP')  # create an interface
root.geometry('860x260')  # increased height to fit all elements

# Add empty row for spacing at top with reduced padding
empty_label = Label(root, text="")
empty_label.grid(row=0, column=0, pady=3)  # reduced padding from 10 to 5

# select by year - shifted to row 1
Label(text='start year:').grid(row=1, column=0)
entry = Entry()  # enter the start year
entry.grid(row=1, column=1)  # position for entry
Label(text='end year:').grid(row=1, column=2)
entry1 = Entry()  # enter the end year
entry1.grid(row=1, column=3)  # position for entry1

# Buttons on the top row - reorganized from left to right - shifted to row 1
Button(text='metadata', command=fetch_metadata).grid(row=1, column=4, padx=5)
search_create_button = Button(text='search & create', command=search_create)
search_create_button.grid(row=1, column=5, padx=5)  # search &create the target sub-dataset
Button(text='file_select', command=file_select).grid(row=1, column=6, padx=5)

# select by single lat/lon - shifted to row 2
Label(text='lat(*100):').grid(row=2, column=0)
entry2 = Entry()  # enter lat
entry2.grid(row=2, column=1)  # position for entry2
Label(text='lon(*100):').grid(row=2, column=2)
entry3 = Entry()  # enter the end year
entry3.grid(row=2, column=3)  # position for entry3

# region combobox - shifted to row 3
Label(text='region:').grid(row=3, column=0)
comvalue1 = tk.StringVar()
comboxlist1 = ttk.Combobox(root, textvariable=comvalue1)  
comboxlist1["values"] = ("all", "africa", "asia", "australia", "canada", "europe", "mexico", "southamerica", "usa")
comboxlist1.grid(row=3, column=1)
comboxlist1.current(0)  

# species combobox - shifted to row 3
Label(text='species:').grid(row=3, column=2)
comvalue = tk.StringVar()
comboxlist = ttk.Combobox(root, textvariable=comvalue)  
comboxlist["values"] = ("all", "ABAL", "ABAM", "ABBI", "ABBA", "ABBO", "ABCE", "ABCI", "ABCO", 
                        "ABDE", "ABDU", "ABFO", "ABJA", "ABKO", "ABLA", "ABMA", "ABNO",
                        "ABPI", "ABPN", "ABPR", "ABRC", "ABSB", "ABSP", "ACRU", "ACSA", "ACSH", 
                        "ADCO", "ADDI", "ADHO", "ADUS", "AFXY", "AGAU", "AIOC", "ALAC", "ALCR", 
                        "ALSP", "ALTR", "AMCE", "APMA", "ARAN", "ARAR", "ASCA", "ASCS", "ASMU", 
                        "ASPO", "ASPY", "ASSU", "ASTO", "ATCU", "ATSE", "AUCH", "BAPL", "BAPR", 
                        "BEAK", "BEAL", "BEER", "BELE", "BEPA", "BEPU", "BESP", "BEUT", "BRBO", 
                        "BRSP", "BUAF", "BUGR", "CABU", "CACO", "CAIN", "CANO", "CAPY", "CARO", 
                        "CASA", "CDAT", "CDBR", "CDDE", "CDLI", "CEAN", "CECA", "CEFI", "CEMC", 
                        "CEMO", "CENE", "CEOD", "CESA", "CESP", "CHAX", "CHER", "CHLA", "CHNO",
                        "CHOB", "CHTH", "CKTA", "CMJA", "CNPL", "COLU", "COPA", "CPBE", "CUCH", 
                        "CYGL", "CYOV", "CYTE", "DABI", "DACO", "DRLO", "DRSP", "ENCY", "ERAF", 
                        "ERIV", "FAGR", "FAOR", "FASY", "FICU", "FOHO", "FRAM", "FREX", "FRNI", 
                        "GEAM", "GOGL", "HABI", "HAIM", "HAIP", "HAOC", "HASE", "HEFO", "HEHE", 
                        "HUCR", "HUPR", "HYCO", "HYST", "JACO", "JGAU", "JGNE", "JGNI", "JUCO", 
                        "JUAU", "JUEX", "JUFO", "JUOC", "JUOS", "JUPC", "JUPH", "JUPR", "JURE", 
                        "JUSC", "JUSP", "JUTI", "JUTU", "JUVI", "LADA", "LADE", "LAGM", "LAGR", 
                        "LALA", "LALY", "LAOC", "LASI", "LASP", "LGFR", "LIBI", "LIDE", "LITU", 
                        "MIXD", "NOBE", "NOGU", "NOPB", "NOPD", "NOPU", "NOSO", "PCAB", "PCCH", 
                        "PCEN", "PCEX", "PCGL", "PCGN", "PCLI", "PCMA", "PCOB", "PCOM", "PCOR", 
                        "PCPU", "PCRU", "PCSH", "PCSI", "PCSM", "PCSP", "PCTI", "PHAS", "PHGL", 
                        "PHTR", "PIAL", "PIAM", "PIAR", "PIAZ", "PIBA", "PIBN", "PIBR", "PICE", 
                        "PICM", "PICO", "PICU", "PIDE", "PIEC", "PIED", "PIFL", "PIGE", "PIGR",
                        "PIHA", "PIHE", "PIHR", "PIJE", "PIKE", "PIKO", "PILA", "PILE", "PILO", 
                        "PIMA", "PIMG", "PIMK", "PIMR", "PIMU", "PIMZ", "PINE", "PINI", "PIPA", 
                        "PIPE", "PIPI", "PIPN", "PIPO", "PIPU", "PIRE", "PIRI", "PIRO", "PISF", 
                        "PISI", "PISP", "PIST", "PISY", "PITA", "PITB", "PITO", "PIUN", "PIUV", 
                        "PIVI", "PIWA", "PLRA", "PONI", "PPDE", "PPGR", "PPSP", "PPTM", "PPTR", 
                        "PRMA", "PROS", "PSMA", "PSME", "PTAN", "PTLE", "QUAL", "QUCA", "QUCE", 
                        "QUCF", "QUCN", "QUCO", "QUDG", "QUFA", "QUFG", "QUHA", "QULO", "QULY", 
                        "QUMA", "QUMC", "QUMO", "QUMU", "QUPA", "QUPE", "QUPR", "QUPU", "QURO", 
                        "QURU", "QUSH", "QUSP", "QUST", "QUVE", "RO", "SALA", "SAPC", "TABA", 
                        "TADI", "TAMU", "TEGR", "THOC", "THPL", "TICO", "TSCA", "TSCR", "TSDI", 
                        "TSDU", "TSHE", "TSME", "ULSP", "VIKE", "WICE")
comboxlist.grid(row=3, column=3)
comboxlist.current(0)  # select the first one as default

# Add a horizontal separator line
separator = Frame(root, height=2, bd=1, relief=SUNKEN)
separator.grid(row=4, column=0, columnspan=7, sticky=EW, padx=5, pady=10)

# Add metadata file selection with browse button - below region/species - shifted to row 5
Label(text='Metadata file:').grid(row=5, column=0, sticky=W, padx=5, pady=10)
metadata_path_entry = Entry(root, width=50)
metadata_path_entry.grid(row=5, column=1, columnspan=3, sticky=W+E, padx=5, pady=10)
Button(text='Browse...', command=browse_metadata_file).grid(row=5, column=4, padx=5, pady=10)

# Add source repository selection with browse button - below metadata - shifted to row 6
Label(text='Data Source:').grid(row=6, column=0, sticky=W, padx=5, pady=10)
source_path_entry = Entry(root, width=50)
source_path_entry.grid(row=6, column=1, columnspan=3, sticky=W+E, padx=5, pady=10)
Button(text='Browse...', command=browse_source_repository).grid(row=6, column=4, padx=5, pady=10)

loop = mainloop()  # go!
