import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import random

def file_select():
    fk = filedialog.askopenfilenames(title="select TR files")
    if fk:
        configuration_dialog(fk)

def configuration_dialog(fk):
    def apply_correction():
        if var_correction.get() == 1:
            plot_allometry(fk, random.uniform(0, 1))
        elif var_correction.get() == 2:
            try:
                value = float(entry.get())
                plot_allometry(fk, value)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")
        elif var_correction.get() == 3:
            try:
                min_value = float(entry_min.get())
                max_value = float(entry_max.get())
                if min_value < max_value:
                    value = random.uniform(min_value, max_value)
                    plot_allometry(fk, value)
                else:
                    messagebox.showerror("Invalid Range", "Min value should be less than Max value.")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers.")
        
        # Handle DBH calculation method
        dbh_method = var_dbh.get()
        print(f"DBH Calculation Method: {dbh_method}")
        
        # Handle file output path
        output_path = entry_output_path.get()
        print(f"File Output Path: {output_path}")
        
        dialog.destroy()

    def update_ui():
        if var_correction.get() == 1:
            entry_frame.grid_remove()
            random_frame.grid_remove()
        elif var_correction.get() == 2:
            entry_frame.grid()
            random_frame.grid_remove()
        elif var_correction.get() == 3:
            entry_frame.grid_remove()
            random_frame.grid()

    def select_output_path():
        path = filedialog.askdirectory(title="Select Output Path")
        if path:
            entry_output_path.delete(0, tk.END)
            entry_output_path.insert(0, path)

    dialog = tk.Toplevel(root)
    dialog.title("Configuration")
    dialog.geometry('800x300')
    dialog.transient(root)  # Make the dialog appear above the root window

    # Configure grid columns and rows to have equal weight
    for i in range(2):
        dialog.grid_columnconfigure(i, weight=1, minsize=300)
    for i in range(3):
        dialog.grid_rowconfigure(i, weight=1)

    # Initial Width Bias Correction Group Box
    group_box_correction = tk.LabelFrame(dialog, text="Initial Width Bias Correction")
    group_box_correction.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    var_correction = tk.IntVar(value=1)
    tk.Radiobutton(group_box_correction, text="No", variable=var_correction, value=1, command=update_ui).grid(row=0, column=0, padx=10, pady=5)
    tk.Radiobutton(group_box_correction, text="Customize", variable=var_correction, value=2, command=update_ui).grid(row=0, column=1, padx=10, pady=5)
    tk.Radiobutton(group_box_correction, text="Random", variable=var_correction, value=3, command=update_ui).grid(row=0, column=2, padx=10, pady=5)

    entry_frame = tk.Frame(group_box_correction)
    entry_frame.grid(row=1, column=0, columnspan=3, pady=5)
    entry_frame.grid_remove()
    tk.Label(entry_frame, text="Value:").pack(side=tk.LEFT, padx=5)
    entry = tk.Entry(entry_frame)
    entry.pack(side=tk.LEFT, padx=5)

    random_frame = tk.Frame(group_box_correction)
    random_frame.grid(row=1, column=0, columnspan=3, pady=5)
    random_frame.grid_remove()
    tk.Label(random_frame, text="Min:").pack(side=tk.LEFT, padx=5)
    entry_min = tk.Entry(random_frame)
    entry_min.pack(side=tk.LEFT, padx=5)
    tk.Label(random_frame, text="Max:").pack(side=tk.LEFT, padx=5)
    entry_max = tk.Entry(random_frame)
    entry_max.pack(side=tk.LEFT, padx=5)

    # DBH Calculation Method Group Box
    group_box_dbh = tk.LabelFrame(dialog, text="DBH Calculation Method")
    group_box_dbh.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    var_dbh = tk.IntVar(value=1)
    tk.Radiobutton(group_box_dbh, text="Lockwood", variable=var_dbh, value=1).grid(row=0, column=0, padx=10, pady=5, sticky="w")
    tk.Radiobutton(group_box_dbh, text="Aggregation with bark estimation", variable=var_dbh, value=2).grid(row=1, column=0, padx=10, pady=5, sticky="w")

    # Select File Output Path Group Box
    group_box_output = tk.LabelFrame(dialog, text="Select File Output Path")
    group_box_output.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

    entry_output_path = tk.Entry(group_box_output)
    entry_output_path.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    tk.Button(group_box_output, text="Select", command=select_output_path).grid(row=0, column=1, padx=10, pady=5)

    group_box_output.grid_columnconfigure(0, weight=1)

    # Apply Button
    apply_button = tk.Button(dialog, text="Apply", command=apply_correction, width=20)
    apply_button.grid(row=2, column=0, columnspan=2, pady=10)
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=1)

def plot_allometry(fk, value):
    print(f"Correction Value: {value}")
    # 这里是你的 plot_allometry 函数的实现
    # ...

root = tk.Tk()
root.title('ITRDB_search')  # create an interface
root.geometry('650x150')  # size and position

# select by year
tk.Label(root, text='start year：').grid(row=0, column=0, padx=10, pady=10)
entry = tk.Entry(root)  # enter the start year
entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")  # position for entry
tk.Label(root, text='end year：').grid(row=0, column=2, padx=10, pady=10)
entry1 = tk.Entry(root)  # enter the end year
entry1.grid(row=0, column=3, padx=10, pady=10, sticky="ew")  # position for entry1

tk.Button(root, text='file_select', command=file_select).grid(row=1, column=1, columnspan=3, pady=20, sticky="ew")
root.mainloop()