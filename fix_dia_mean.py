import pandas as pd
import os
import glob
import numpy as np

# Define input/output directories
input_dir = "test_output/test_file_select_fixed"
output_dir = "test_output/test_file_select_fixed_mean_cols"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Get all mean files
mean_files = glob.glob(os.path.join(input_dir, "*_mean*.csv"))
print(f"Found {len(mean_files)} mean files")

# Process each mean file
for file_path in mean_files:
    file_name = os.path.basename(file_path)
    print(f"Processing {file_name}")
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check if we have at least Year column
        if 'Year' not in df.columns:
            print(f"Warning: No 'Year' column in {file_name}, skipping")
            continue
            
        # Get all the non-Year columns
        value_cols = [col for col in df.columns if col != 'Year' and col != 'samp.depth']
        
        if not value_cols:
            print(f"Warning: No data columns in {file_name}, skipping")
            continue
            
        # Create new dataframe with Year column first
        fixed_df = pd.DataFrame({'Year': df['Year']})
        
        # Determine variable type from filename
        var_type = None
        if 'dia_mean' in file_name:
            var_type = 'dia'
        elif 'bio_mean' in file_name:
            var_type = 'bio'
        elif 'delta_dia_mean' in file_name:
            var_type = 'delta_dia'
        elif 'delta_bio_mean' in file_name:
            var_type = 'delta_bio'
        elif 'age_mean' in file_name:
            var_type = 'age'
        elif 'diaa_mean' in file_name:
            var_type = 'diaa'
        elif 'bioo_mean' in file_name:
            var_type = 'bioo'
        elif 'delta_diaa_mean' in file_name:
            var_type = 'delta_diaa'
        elif 'delta_bioo_mean' in file_name:
            var_type = 'delta_bioo'
            
        # Process columns and add to dataframe
        if var_type is None:
            print(f"Warning: Could not determine variable type for {file_name}, using generic name")
            # Just copy original column names but add a consistent 'mean_' prefix
            for i, col in enumerate(value_cols):
                if not col.startswith('mean_'):
                    new_col = f"mean_{col}"
                else:
                    new_col = col
                fixed_df[new_col] = df[col]
        else:
            # Create a properly named mean column
            mean_col_name = f"mean_{var_type}"
            
            # If there's only one value column, use it directly
            if len(value_cols) == 1:
                fixed_df[mean_col_name] = df[value_cols[0]]
            else:
                # If there are multiple columns, calculate their mean
                fixed_df[mean_col_name] = df[value_cols].mean(axis=1)
                # Also keep original columns with proper naming
                for col in value_cols:
                    if not col.startswith('mean_'):
                        new_col = f"mean_{col}"
                    else:
                        new_col = col
                    fixed_df[new_col] = df[col]
        
        # Add samp.depth column AFTER the mean values
        if 'samp.depth' in df.columns:
            fixed_df['samp.depth'] = df['samp.depth']
            print(f"Preserved samp.depth column in {file_name}")
        else:
            # Add samp.depth column with counts of non-NaN values from original columns
            fixed_df['samp.depth'] = df[value_cols].count(axis=1)
            print(f"Added samp.depth column in {file_name}")
                    
        # Save the fixed file
        output_path = os.path.join(output_dir, file_name)
        fixed_df.to_csv(output_path, index=False)
        print(f"Saved fixed file: {output_path}")
        
    except Exception as e:
        print(f"Error processing {file_name}: {str(e)}")

print("All mean files processed successfully") 