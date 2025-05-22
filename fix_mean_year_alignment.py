import pandas as pd
import os
import glob
import numpy as np

# Define the input/output directories
input_dir = "test_output/test_file_select"
output_dir = "test_output/test_file_select_fixed_years"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Get list of mean files
mean_files = glob.glob(os.path.join(input_dir, "*_mean*.csv"))

# Function to fix year alignment in a mean file
def fix_year_alignment(file_path):
    print(f"Processing {os.path.basename(file_path)}")
    
    # First, check if there's a non-mean version of this file
    file_name = os.path.basename(file_path)
    base_name = file_name.replace("_mean", "")
    base_file_path = os.path.join(input_dir, base_name)
    correction_part = ""
    
    # Handle correction files
    if "correction" in file_name:
        # Extract the correction parameters
        parts = file_name.split("_correction_")
        if len(parts) > 1:
            correction_part = "_correction_" + parts[1]
            base_name = parts[0].replace("_mean", "") + correction_part
            base_file_path = os.path.join(input_dir, base_name)
    
    # Read both files
    try:
        mean_df = pd.read_csv(file_path)
        
        # Check if the base file exists
        if not os.path.exists(base_file_path):
            print(f"Base file {base_file_path} not found")
            return None
            
        base_df = pd.read_csv(base_file_path)
        
        # Check columns to determine what variable we're working with
        variable_columns = [col for col in mean_df.columns if col != "Year"]
        if not variable_columns:
            print(f"No variable columns found in {file_name}")
            return None
            
        # Identify the years from the base file
        years = base_df["Year"].values
        
        # Get the mean values
        mean_values = mean_df[variable_columns].values
        
        # Check if mean_values has data
        if len(mean_values) == 0 or np.isnan(mean_values).all():
            print(f"No valid mean values found in {file_name}")
            return None
            
        # Create new dataframe with correct years
        fixed_df = pd.DataFrame({"Year": years})
        
        # Calculate mean rows to data rows ratio
        ratio = len(years) / len(mean_values)
        
        # Two typical cases:
        # 1. If ratio is close to 1: Simple misalignment
        # 2. If ratio is close to 2: Need to extract every other value
        
        if 0.9 < ratio < 1.1:  # Case 1: Almost the same length, just need alignment
            print(f"Case 1: Simple alignment needed (ratio={ratio:.2f})")
            # If mean_values is longer, trim it
            if len(mean_values) >= len(years):
                for i, col in enumerate(variable_columns):
                    fixed_df[col] = mean_values[:len(years), i]
            else:
                # If mean_values is shorter, pad with NaN
                for i, col in enumerate(variable_columns):
                    padded_values = np.full(len(years), np.nan)
                    padded_values[:len(mean_values)] = mean_values[:, i]
                    fixed_df[col] = padded_values
        
        elif 1.9 < ratio < 2.1:  # Case 2: Double the rows, need to extract calculated values
            print(f"Case 2: Alternate value extraction needed (ratio={ratio:.2f})")
            # Calculate starting offset by checking where values start to appear
            offset = 0
            for i in range(len(mean_values)):
                if not np.isnan(mean_values[i]).all():
                    offset = i
                    break
                    
            print(f"Found values starting at offset {offset}")
            
            # Extract values from alternating positions
            result_rows = len(years)
            for i, col in enumerate(variable_columns):
                fixed_values = np.full(result_rows, np.nan)
                
                # Map values from mean_df to fixed_df
                valid_entries = min(len(mean_values) - offset, (result_rows + 1) // 2)
                for j in range(valid_entries):
                    src_idx = j + offset
                    if src_idx < len(mean_values):
                        tgt_idx = j
                        if tgt_idx < result_rows:
                            fixed_values[tgt_idx] = mean_values[src_idx, i]
                
                fixed_df[col] = fixed_values
        
        else:  # Other cases, try a more generic mapping
            print(f"Case 3: Complex mapping needed (ratio={ratio:.2f})")
            # Find non-NaN values in mean_values
            non_nan_indices = []
            for i in range(len(mean_values)):
                if not np.isnan(mean_values[i]).all():
                    non_nan_indices.append(i)
            
            if not non_nan_indices:
                print(f"No non-NaN values found in {file_name}")
                return None
                
            # Get first and last non-NaN indices
            first_idx = non_nan_indices[0]
            last_idx = non_nan_indices[-1]
            
            # Calculate stretching factor for mapping
            mean_range = last_idx - first_idx + 1
            year_range = len(years)
            stretch_factor = year_range / mean_range
            
            # Create fixed values
            for i, col in enumerate(variable_columns):
                fixed_values = np.full(year_range, np.nan)
                
                # Map each value from mean_df to fixed_df
                for j in range(first_idx, last_idx + 1):
                    # Calculate target index in the output array
                    target_idx = int((j - first_idx) * stretch_factor)
                    if 0 <= target_idx < year_range:
                        fixed_values[target_idx] = mean_values[j, i]
                
                fixed_df[col] = fixed_values
        
        return fixed_df
        
    except Exception as e:
        print(f"Error processing {file_name}: {str(e)}")
        return None

# Process all mean files
for file_path in mean_files:
    file_name = os.path.basename(file_path)
    
    # Fix the alignment
    fixed_df = fix_year_alignment(file_path)
    
    if fixed_df is not None:
        # Save the fixed file
        output_path = os.path.join(output_dir, file_name)
        fixed_df.to_csv(output_path, index=False)
        print(f"Saved {output_path}")

print("Done fixing year alignment in mean files.") 