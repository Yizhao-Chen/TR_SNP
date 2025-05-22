import matplotlib.pyplot as plt
import pandas as pd
import os
import tkinter as tk # For dialogs
from tkinter import filedialog, messagebox

def generate_visualization(plot_info: dict, output_data_path: str) -> tuple[bool, str | None]:
    """
    Generates and displays a visualization based on plot_info.

    Args:
        plot_info (dict): Dictionary containing parsed plot information.
                          Expected keys: "type", "data_file", "x_column", "y_column".
                          Optional keys: "title", "xlabel", "ylabel".
        output_data_path (str): The directory where the CSV data files are located.

    Returns:
        tuple[bool, str | None]: (success_boolean, message_string). 
                                 If success_boolean is False, message_string contains the error.
                                 If success_boolean is True, message_string is None.
    """
    if not all(key in plot_info for key in ["type", "data_file", "x_column", "y_column"]):
        error_msg = "Plotting Error: Plot information is incomplete. Missing required keys (type, data_file, x_column, y_column)."
        print(error_msg)
        return False, error_msg

    data_file_name = plot_info["data_file"] # For user-friendly messages
    data_file_path = os.path.join(output_data_path, data_file_name)

    try:
        df = pd.read_csv(data_file_path)
    except FileNotFoundError:
        error_msg = f"Plotting Error: Data file '{data_file_name}' not found at '{data_file_path}'."
        print(error_msg)
        return False, error_msg
    except pd.errors.EmptyDataError:
        error_msg = f"Plotting Error: Data file '{data_file_name}' is empty."
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Plotting Error: Could not read data from '{data_file_name}': {e}"
        print(error_msg)
        return False, error_msg

    x_col_name = plot_info["x_column"]
    y_col_name = plot_info["y_column"]
    required_columns = [x_col_name, y_col_name]
    
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        error_msg = f"Plotting Error: Column(s) '{', '.join(missing_cols)}' not found in data file '{data_file_name}'. Available columns: {list(df.columns)}."
        print(error_msg)
        return False, error_msg

    plt.figure() # Create a new figure for each plot

    plot_type = plot_info["type"].lower()

    try:
        if plot_type == "line":
            plt.plot(df[plot_info["x_column"]], df[plot_info["y_column"]])
        elif plot_type == "bar":
            plt.bar(df[plot_info["x_column"]], df[plot_info["y_column"]])
        elif plot_type == "scatter":
            plt.scatter(df[x_col_name], df[y_col_name])
        else:
            error_msg = f"Plotting Error: Unknown plot type '{plot_info['type']}'. Supported types: line, bar, scatter."
            print(error_msg)
            return False, error_msg
    except Exception as e:
        error_msg = f"Plotting Error: An error occurred while generating the {plot_type} plot: {e}"
        print(error_msg)
        return False, error_msg

    plt.title(plot_info.get("title", "LLM Suggested Plot"))
    plt.xlabel(plot_info.get("xlabel", x_col_name)) 
    plt.ylabel(plot_info.get("ylabel", y_col_name))
    
    plt.xticks(rotation=45, ha="right") # Improve x-axis label readability
    plt.tight_layout() # Adjust layout to prevent labels from overlapping
    
    fig = plt.gcf() # Get current figure BEFORE showing it
    
    plt.show() # This will be blocking. User views and closes the plot.

    print(f"Plot '{plot_info.get('title', 'LLM Suggested Plot')}' was displayed and closed by user.")

    # Ask user if they want to save the plot
    # Need a temporary root for the dialog if not running within a Tkinter app's mainloop
    # However, this script is called from TR_SNP.py which has a root.
    # To make this function usable standalone for testing, we might need a temp root.
    # For now, assume it's called in an environment where Tkinter is initialized.
    # If running __main__, a root window will be created by messagebox.
    
    # Create a hidden root window if one doesn't exist (for messagebox parenting)
    # This is generally not ideal but helps if function is called outside a Tkinter main app context for this dialog.
    # In our case, TR_SNP.py (the caller) *is* a Tkinter app.
    # No, this is bad practice. Messagebox should work if Tk is imported.
    # Let's rely on the fact that TR_SNP.py has Tkinter initialized.
    
    try:
        # Check if a root window exists, useful if running outside full Tkinter app
        # This is a bit of a hack. Ideally, the root window context is managed by the caller.
        # For this specific integration, TR_SNP.py (caller) *has* a root window.
        # So, direct calls to messagebox should be fine.
        if tk._default_root is None:
            # Create a dummy root for the dialog if none exists (e.g. running script directly)
            # This is often problematic. Best to ensure Tkinter is properly initialized by the calling environment.
            # For this task, we'll assume TR_SNP.py (the caller) initializes Tkinter.
            # So, messagebox calls should work without manually creating a root here.
            pass # Proceeding with assumption that Tkinter is initialized by caller

        save_plot = messagebox.askyesno(
            "Save Plot", 
            "Would you like to save the plot you just viewed?",
            # parent= # Ideally parent to the TR_SNP.py window if possible, but direct call should work.
        )
            
        if save_plot:
            default_filename = plot_info.get("title", "llm_suggested_plot").replace(" ", "_").lower() + ".png"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), 
                           ("PDF files", "*.pdf"), 
                           ("JPEG files", "*.jpg"),
                           ("SVG files", "*.svg"),
                           ("All files", "*.*")],
                initialfile=default_filename,
                title="Save Plot As..."
            )
            if file_path:
                try:
                    fig.savefig(file_path, bbox_inches='tight')
                    messagebox.showinfo("Plot Saved", f"Plot saved successfully to:\n{file_path}")
                    print(f"Plot saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save plot: {e}")
                    print(f"Failed to save plot: {e}")
            else:
                print("Plot saving cancelled by user.")
        else:
            print("User chose not to save the plot.")
            
    except tk.TclError as e:
        # This can happen if Tkinter is not properly initialized (e.g. no mainloop running from caller)
        # Or if _default_root is manipulated incorrectly.
        print(f"Tkinter error during save plot dialog: {e}. Plot saving skipped. Ensure GUI is running.")
    except Exception as e:
        print(f"An unexpected error occurred during plot saving dialog: {e}")
        # Continue, as the plot was shown. The error is in saving.
        # The function primarily reports on generation success.

    return True, None # Plot generated and shown, save attempt handled.

if __name__ == '__main__':
    print("Testing llm_plotter.py directly...")

    # Create a dummy CSV file for testing in a 'test_output_data' directory
    dummy_data_path = "test_output_data"
    if not os.path.exists(dummy_data_path):
        os.makedirs(dummy_data_path)
    
    dummy_csv_file = os.path.join(dummy_data_path, "sample_data.csv")
    sample_df_data = {
        'Year': [2000, 2001, 2002, 2003, 2004],
        'ValueA': [10, 12, 15, 13, 17],
        'ValueB': [5, 7, 6, 8, 7],
        'Category': ['C1', 'C2', 'C1', 'C3', 'C2']
    }
    sample_df = pd.DataFrame(sample_df_data)
    sample_df.to_csv(dummy_csv_file, index=False)

    # Test case 1: Line plot
    print("\n--- Test Case 1: Line plot ---")
    plot_info_line = {
        "type": "line",
        "data_file": "sample_data.csv",
        "x_column": "Year",
        "y_column": "ValueA",
        "title": "Line Plot of ValueA over Year",
        "xlabel": "Year (AD)",
        "ylabel": "Measured Value A"
    }
    success, msg = generate_visualization(plot_info_line, dummy_data_path)
    print(f"Test Case 1: Success: {success}, Message: {msg}")

    # Test case 2: Bar plot
    print("\n--- Test Case 2: Bar plot ---")
    plot_info_bar = {
        "type": "bar",
        "data_file": "sample_data.csv", # Using the same file
        "x_column": "Category",
        "y_column": "ValueB",
        "title": "Bar Plot of ValueB by Category"
    }
    # For a meaningful bar plot of categories, we might need to aggregate first
    # But for this test, we'll plot raw values if categories repeat.
    # A more robust LLM suggestion would suggest aggregated data.
    success, msg = generate_visualization(plot_info_bar, dummy_data_path)
    print(f"Test Case 2: Success: {success}, Message: {msg}")

    # Test case 3: Scatter plot
    print("\n--- Test Case 3: Scatter plot ---")
    plot_info_scatter = {
        "type": "scatter",
        "data_file": "sample_data.csv",
        "x_column": "ValueA",
        "y_column": "ValueB",
        "title": "Scatter Plot of ValueA vs ValueB"
    }
    success, msg = generate_visualization(plot_info_scatter, dummy_data_path)
    print(f"Test Case 3: Success: {success}, Message: {msg}")

    # Test case 4: File not found
    print("\n--- Test Case 4: File not found ---")
    plot_info_file_not_found = {
        "type": "line",
        "data_file": "non_existent_data.csv",
        "x_column": "Year",
        "y_column": "ValueA",
        "title": "File Not Found Test"
    }
    success, msg = generate_visualization(plot_info_file_not_found, dummy_data_path)
    print(f"Test Case 4: Success: {success}, Message: {msg}")
    assert not success
    assert "not found" in msg.lower()

    # Test case 5: Column not found
    print("\n--- Test Case 5: Column not found ---")
    plot_info_col_not_found = {
        "type": "line",
        "data_file": "sample_data.csv",
        "x_column": "NonExistentColumn",
        "y_column": "ValueA",
        "title": "Column Not Found Test"
    }
    success, msg = generate_visualization(plot_info_col_not_found, dummy_data_path)
    print(f"Test Case 5: Success: {success}, Message: {msg}")
    assert not success
    assert "not found in data file" in msg.lower()
    
    # Test case 6: Missing required keys in plot_info
    print("\n--- Test Case 6: Missing required keys ---")
    plot_info_missing_keys = {
        "type": "line",
        "data_file": "sample_data.csv",
        # "x_column": "Year", # Missing x_column
        "y_column": "ValueA",
        "title": "Missing Keys Test"
    }
    success, msg = generate_visualization(plot_info_missing_keys, dummy_data_path)
    print(f"Test Case 6: Success: {success}, Message: {msg}")
    assert not success
    assert "missing required keys" in msg.lower()

    # print("\nCleaning up test files...")
    # os.remove(dummy_csv_file)
    # os.rmdir(dummy_data_path)
    # print("Test files cleaned up.")
    print("\nNote: Plots are displayed sequentially and are blocking. Close each plot window to proceed with tests.")
