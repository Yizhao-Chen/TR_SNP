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
# =====================================================================================================

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import *
from shutil import copyfile
import fnmatch
import os

# local functions
import GFNWE
import open_metafile
import plot_all_temporal
from plot_all_temporal import *
from plot_all_allometry import *
from plot_all_allometry_species import *
from plot_age_only import *
# import search_reorganize

# for rpy2 test Yizhao 2019/7/2
import platform
import rpy2.situation
# for rpy2 test Yizhao 2019/7/3
import sys

# define the global variables
# namelist =[]
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

# for rpy2 test Yizhao 2019/7/2
# lib_path = rpy2.situation.get_r_home()
# print(lib_path)
# for rpy2 test Yizhao 2019/7/3
if getattr(sys, 'frozen', False):
    # The application is frozen
    # reset R_HOME and try to find a R installation using the fallback mechanisms
    del os.environ['R_HOME']
    os.environ['R_HOME'] = rpy2.situation.get_r_home()
lib_path = rpy2.situation.get_r_home()
print(lib_path)


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


# open metafile


def select_folder():
    fd = filedialog.askdirectory()
    print(fd)
    return fd


# def select_region():
def search_create():
    returnlist = metafile()
    if returnlist == []:  # no matched data
        messagebox.showerror("error", "no data fit")
        return
    fd = filedialog.askdirectory(title="select repository for output")  # select_folder()
    # if not entry.get() or not entry1.get():  # to check if the inputs of years
    #     messagebox.showerror("error", "plz enter years")  # pump a box out
    #     return  # end if nothing there
    if fd == "":
        messagebox.showerror("error", "plz select repository for output")
        return

    file_path =  os.path.join(fd, "sub_log.txt")
    with open(file_path, 'w') as f:
        for i in range(0, len(returnlist)):
            f.write(str(returnlist[i]))
            f.write('\n')
    path = filedialog.askdirectory(title="select the source repository")
    if path == "":
        messagebox.showerror("error", "plz select the source repository")
        return
    else:
        # path = "D:\MEGA\Live_cases\Hybrid\Tree_ring_data_collection_NOAA_ITRDB\Appendix S1\Cleaned datasets\itrdb-v713-cleaned-rwl"
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
                    #dir = os.path.join(fd, fname1)
                    #copyfile(root + "\\" + fname1, fd + "\\" + fname1)
                    #dir = fd + "\\" + fname1
                    print(fname1)  # the select files
        #plot_R(output_fl, returnlist, fname1)
        plot_R(output_fl, output_fn)
    # Button(text='save', command=lambda:plot_R(returnlist)).grid(row=1, column=4)


def plot_R(output_fl, output_fn):
    print(f"output_fl: {output_fl}")
    print(f"output_fn: {output_fn}")
    if not output_fl:
        messagebox.showerror("error", "plz select the target repository")
        return
    
    output_fn.insert(0, "all")
    Button(text='plot', command=lambda: on_click(output_fl, output_fn)).grid(row=1, column=4)
    #Button(text='plot', command=lambda: on_click(fd)).grid(row=1, column=4)
    # window pop-up for plot
    # print(returnlist)


def on_click(output_fl,output_fn):
    tl = Toplevel()
    tl.geometry('260x100')
    comvalue2 = tk.StringVar()
    # Label(tl, text='test').pack()
    comboxlist2 = ttk.Combobox(tl, textvariable=comvalue2)  # 初始化
    # comboxlist2.bind("<<ComboboxSelected>>",getvaluetest)
    comboxlist2["values"] = output_fn
    comboxlist2.grid(row=0, column=0,padx=20, pady=15)
    print(output_fn)
    comboxlist2.current(0)  # select the first one as default
    # kk = comboxlist2.get()
    #tk.Button(tl, text='go', command=lambda: plot_all(fd, comboxlist2.get(), returnlist)).grid(row=2, column=5)
    tk.Button(tl, text='go', command=lambda: plot_all_ometry(output_fl,comboxlist2.current())).grid(row=1, column=0, padx=20, pady=15)
    # go(comboxlist2,fd,fname1)
    tl.wait_window()
    return

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
    mf = os.path.join(os.path.dirname(__file__), "rwl_metadata_ITRDB.csv")
    with open(mf, mode='r') as infile:
        reader = csv.DictReader(infile)
        name_list = [row['name'] for row in reader]

    fk = filedialog.askopenfilenames(title="select TR files")
    print(fk)
    
    if fk:
        file_names_in_csv = all(os.path.basename(file).split('.')[0] in name_list for file in fk)
        configuration_dialog(fk, file_names_in_csv)

def configuration_dialog(fk, file_names_in_csv=True):
    # 初始化每个文件的 initbias 列表为全 0
    file_Column_Randoms = [[0] * len(r['read.tucson'](file_path).colnames) for file_path in fk]

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
        
        # Handle Bark method
        bark_method = var_bark.get()
        
        # Handle file output path
        output_path = entry_output_path.get()
        
        print(f"min_max_times:", min_value,max_value,times)

        if file_names_in_csv:
            plot_allometry(fk, min_value,max_value,times, file_Column_Randoms,dbh_method, bark_method , output_path)
        else:
            region = comboxlist1.get()
            species = comboxlist.get()
            plot_allometry_species(fk, min_value,max_value,times, file_Column_Randoms,dbh_method, bark_method,output_path, region, species)
            
        dialog.destroy()

    def select_csv(file_path, index):
        # 选择 CSV 文件
        csv_file = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not csv_file:
            return  # 不更新 initbias 列表

        # 读取 CSV 文件并生成字典
        df = pd.read_csv(csv_file)
        sample_to_bias = dict(zip(df['sample'], df['initbias']))

        # 使用 rpy2 读取文件并获取列名
        TR_input = r['read.tucson'](file_path)
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            pdf_input = rpy2.robjects.conversion.ri2py(TR_input)

        # 生成 initbias 列表
        initbias_list = []
        for col_name in pdf_input.columns:
            if col_name in sample_to_bias:
                try:
                    initbias_list.append(int(sample_to_bias[col_name]))
                except ValueError:
                    initbias_list.append(0)
            else:
                messagebox.showerror("Error", f"Sample {col_name} not found in CSV.")
                return

        # 更新对应索引的 initbias 列表
        file_Column_Randoms[index] = initbias_list

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

    def show_samples(file_path):
        # 使用 rpy2 读取文件并获取列名
        TR_input = r['read.tucson'](file_path)
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            pdf_input = rpy2.robjects.conversion.ri2py(TR_input)
        
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
    group_box_correction = tk.LabelFrame(dialog, text="Initial Width Bias Correction")
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

    # DBH Calculation Method Group Box
    group_box_dbh = tk.LabelFrame(dialog, text="DBH Calculation Method")
    group_box_dbh.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    var_dbh = tk.IntVar(value=0)
    tk.Radiobutton(group_box_dbh, text="Lockwood", variable=var_dbh, value=0).grid(row=0, column=0, padx=10, pady=5, sticky="w")
    # tk.Radiobutton(group_box_dbh, text="Aggregation with bark estimation", variable=var_dbh, value=1).grid(row=1, column=0, padx=10, pady=5, sticky="w")
    tk.Radiobutton(group_box_dbh, text="Other Methods", variable=var_dbh, value=1).grid(row=1, column=0, padx=10, pady=5, sticky="w")

    # Bark correction Group Box
    group_box_bark = tk.LabelFrame(dialog, text="Bark Correction")
    group_box_bark.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    var_bark = tk.IntVar(value=0)
    tk.Radiobutton(group_box_bark, text="No", variable=var_bark, value=0).grid(row=0, column=0, padx=10, pady=5, sticky="w")
    tk.Radiobutton(group_box_bark, text="Yes", variable=var_bark, value=1).grid(row=1, column=0, padx=10, pady=5, sticky="w")

    # Select File Output Path Group Box
    group_box_output = tk.LabelFrame(dialog, text="Select File Output Path")
    #group_box_output.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    group_box_output.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

    entry_output_path = tk.Entry(group_box_output)
    entry_output_path.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    tk.Button(group_box_output, text="Select", command=select_output_path).grid(row=0, column=1, padx=10, pady=5)

    group_box_output.grid_columnconfigure(0, weight=1)

    # Region and Species Group Box
    group_box_region_species = tk.LabelFrame(dialog, text="Region and Species")
    group_box_region_species.grid(row=2, column=0, columnspan=2, padx=10, pady=20, sticky="nsew")  # Increased pady for more vertical spacing

    # region combobox
    tk.Label(group_box_region_species, text='region:').grid(row=0, column=0, padx=(10, 2),pady=10)  # Added padx and pady for spacing
    comvalue1 = tk.StringVar()
    comboxlist1 = ttk.Combobox(group_box_region_species, textvariable=comvalue1)  
    comboxlist1["values"] = ("all", "africa", "asia", "australia", "canada", "europe", "mexico", "southamerica", "usa")
    comboxlist1.grid(row=0, column=1, padx=(2, 10), pady=10)  # Added padx and pady for spacing
    
    comboxlist1.current(8)  # Ensure the first item is selected

    # species combobox
    tk.Label(group_box_region_species, text='species:').grid(row=0, column=2, padx=(10, 2) ,pady=10)  # Added padx and pady for spacing
    comvalue = tk.StringVar()
    comboxlist = ttk.Combobox(group_box_region_species, textvariable=comvalue)  
    comboxlist["values"] = ("all", "ABAL", "ABAM", "ABBA", "ABBO", "ABCE", "ABCI", "ABCO", "ABFO", "ABLA", "ABMA", "ABNO",
                            "ABPI", "ABPN", "ABRC", "ABSB", "ABSP", "ACRU", "ACSH", "ADHO", "ADUS", "AGAU", "ARAR",
                            "ATCU", "ATSE", "AUCH", "BELE", "BEPU", "BEUT", "CABU", "CACO", "CADE", "CADN", "CASA",
                            "CDAT", "CDBR", "CDDE", "CDLI", "CEAN", "CEBR", "CEMC", "CESP", "CHER", "CHLA", "CHNO",
                            "CHOB", "CMJA", "CPBE", "CUCH", "CYGL", "CYOV", "DABI", "DRLO", "FAGR", "FASY",
                            "FICU", "FOHO", "FREX", "GOGL", "HABI", "HEHE", "JUAU", "JUEX", "JUFO", "JUOC", "JUOS",
                            "JUPH", "JUPR", "JURE", "JUSC", "JUSP", "JUTI", "JUTU", "JUVI", "LADA", "LADE", "LAGM",
                            "LAGR", "LALA", "LALY", "LAOC", "LASI", "LASP", "LGFR", "LIBI", "LIDE", "LITU", "MIXD",
                            "NOBE", "NOGU", "NOPB", "NOPD", "NOPU", "NOSO", "PCAB", "PCCH", "PCEN", "PCEX", "PCGL",
                            "PCGN", "PCLI", "PCMA", "PCOB", "PCOM", "PCOR", "PCPU", "PCRU", "PCSH", "PCSI", "PCSM",
                            "PCSP", "PCTI", "PHAS", "PHGL", "PHTR", "PIAL", "PIAM", "PIAR", "PIAZ", "PIBA", "PIBN",
                            "PIBR", "PICE", "PICM", "PICO", "PICU", "PIDE", "PIEC", "PIED", "PIFL", "PIGE", "PIGR",
                            "PIHA", "PIHE", "PIHR", "PIJE", "PIKE", "PIKO", "PILA", "PILE", "PILO", "PIMA", "PIMG",
                            "PIMK", "PIMR", "PIMU", "PIMZ", "PINE", "PINI", "PIPA", "PIPE", "PIPI", "PIPN", "PIPO",
                            "PIPU", "PIRE", "PIRI", "PIRO", "PISF", "PISI", "PISP", "PIST", "PISY", "PITA", "PITB",
                            "PITO", "PIUN", "PIUV", "PIVI", "PIWA", "PLRA", "PPDE", "PPGR", "PPSP", "PPTM", "PPTR",
                            "PRMA", "PROS", "PSMA", "PSME", "PTAN", "PTLE", "QUAL", "QUCA", "QUCE", "QUCF", "QUCN",
                            "QUCO", "QUDG", "QUFA", "QUFG", "QUHA", "QULO", "QULY", "QUMA", "QUMC", "QUMO", "QUMU",
                            "QUPA", "QUPE", "QUPR", "QUPU", "QURO", "QURU", "QUSH", "QUSP", "QUST", "QUVE", "SALA",
                            "SAPC", "TABA", "TADI", "TAMU", "TEGR", "THOC", "THPL", "TSCA", "TSCR",
                            "TSDI", "TSDU", "TSHE", "TSME", "ULSP", "VIKE", "WICE")
    comboxlist.grid(row=0, column=3, padx=(2, 10), pady=10)  # Added padx and pady for spacing
    comboxlist.current(1)  # Ensure the first item is selected

    # Center align the group box content
    group_box_region_species.grid_columnconfigure(0, weight=1)
    group_box_region_species.grid_columnconfigure(1, weight=1)
    group_box_region_species.grid_columnconfigure(2, weight=1)
    group_box_region_species.grid_columnconfigure(3, weight=1)
    # Show or hide the region and species group box based on file_names_in_csv
    if file_names_in_csv:
        group_box_region_species.grid_remove()
    else:
        group_box_region_species.grid()
        
    # Apply Button
    apply_button = tk.Button(dialog, text="Apply", command=apply_correction, width=20)
    apply_button.grid(row=3, column=0, columnspan=2, pady=10)
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_columnconfigure(1, weight=1)


# interface design
root = Tk()
root.title('TR_SNP')  # create an interface
root.geometry('800x110')  # size and position

# select by year
Label(text='start year:').grid(row=0, column=0)
entry = Entry()  # enter the start year
entry.grid(row=0, column=1)  # position for entry
Label(text='end year:').grid(row=0, column=2)
entry1 = Entry()  # enter the end year
entry1.grid(row=0, column=3)  # position for entry1

# select by lat/lon
# Label(text='lat_s：    ').grid(row=1,column=0)
# entry2 = Entry()#enter the start year
# entry2.grid(row=1,column=1)#position for entry2
# Label(text='lat_e:    ').grid(row=1,column=2)
# entry3 = Entry()#enter the end year
# entry3.grid(row=1, column=3)#position for entry3
# Label(text='lon_s：    ').grid(row=2,column=0)
# entry4 = Entry()#enter the start year
# entry4.grid(row=2,column=1)#position for entry4
# Label(text='lon_e:    ').grid(row=2,column=2)
# entry5 = Entry()#enter the end year
# entry5.grid(row=2, column=3)#position for entry5

# select by single lat/lon
Label(text='lat(*100):').grid(row=1, column=0)
entry2 = Entry()  # enter lat
entry2.grid(row=1, column=1)  # position for entry2
Label(text='lon(*100):').grid(row=1, column=2)
entry3 = Entry()  # enter the end year
entry3.grid(row=1, column=3)  # position for entry3

# region combobox
Label(text='region:').grid(row=2, column=0)
comvalue1 = tk.StringVar()
comboxlist1 = ttk.Combobox(root, textvariable=comvalue1)  
comboxlist1["values"] = ("all", "africa", "asia", "australia", "canada", "europe", "mexico", "southamerica", "usa")
comboxlist1.grid(row=2, column=1)
comboxlist1.current(0)  

# species combobox
Label(text='species:').grid(row=2, column=2)
comvalue = tk.StringVar()
comboxlist = ttk.Combobox(root, textvariable=comvalue)  
comboxlist["values"] = ("all", "ABAL", "ABAM", "ABBA", "ABBO", "ABCE", "ABCI", "ABCO", "ABFO", "ABLA", "ABMA", "ABNO",
                        "ABPI", "ABPN", "ABRC", "ABSB", "ABSP", "ACRU", "ACSH", "ADHO", "ADUS", "AGAU", "ARAR",
                        "ATCU", "ATSE", "AUCH", "BELE", "BEPU", "BEUT", "CABU", "CACO", "CADE", "CADN", "CASA",
                        "CDAT", "CDBR", "CDDE", "CDLI", "CEAN", "CEBR", "CEMC", "CESP", "CHER", "CHLA", "CHNO",
                        "CHOB", "CMJA", "CPBE", "CUCH", "CYGL", "CYOV", "DABI", "div.DRLO", "FAGR", "FASY",
                        "FICU", "FOHO", "FREX", "GOGL", "HABI", "HEHE", "JUAU", "JUEX", "JUFO", "JUOC", "JUOS",
                        "JUPH", "JUPR", "JURE", "JUSC", "JUSP", "JUTI", "JUTU", "JUVI", "LADA", "LADE", "LAGM",
                        "LAGR", "LALA", "LALY", "LAOC", "LASI", "LASP", "LGFR", "LIBI", "LIDE", "LITU", "MIXD",
                        "NOBE", "NOGU", "NOPB", "NOPD", "NOPU", "NOSO", "PCAB", "PCCH", "PCEN", "PCEX", "PCGL",
                        "PCGN", "PCLI", "PCMA", "PCOB", "PCOM", "PCOR", "PCPU", "PCRU", "PCSH", "PCSI", "PCSM",
                        "PCSP", "PCTI", "PHAS", "PHGL", "PHTR", "PIAL", "PIAM", "PIAR", "PIAZ", "PIBA", "PIBN",
                        "PIBR", "PICE", "PICM", "PICO", "PICU", "PIDE", "PIEC", "PIED", "PIFL", "PIGE", "PIGR",
                        "PIHA", "PIHE", "PIHR", "PIJE", "PIKE", "PIKO", "PILA", "PILE", "PILO", "PIMA", "PIMG",
                        "PIMK", "PIMR", "PIMU", "PIMZ", "PINE", "PINI", "PIPA", "PIPE", "PIPI", "PIPN", "PIPO",
                        "PIPU", "PIRE", "PIRI", "PIRO", "PISF", "PISI", "PISP", "PIST", "PISY", "PITA", "PITB",
                        "PITO", "PIUN", "PIUV", "PIVI", "PIWA", "PLRA", "PPDE", "PPGR", "PPSP", "PPTM", "PPTR",
                        "PRMA", "PROS", "PSMA", "PSME", "PTAN", "PTLE", "QUAL", "QUCA", "QUCE", "QUCF", "QUCN",
                        "QUCO", "QUDG", "QUFA", "QUFG", "QUHA", "QULO", "QULY", "QUMA", "QUMC", "QUMO", "QUMU",
                        "QUPA", "QUPE", "QUPR", "QUPU", "QURO", "QURU", "QUSH", "QUSP", "QUST", "QUVE", "SALA",
                        "SAPC", "species", "TABA", "TADI", "TAMU", "TEGR", "THOC", "THPL", "TSCA", "TSCR",
                        "TSDI", "TSDU", "TSHE", "TSME", "ULSP", "VIKE", "WICE")

comboxlist.grid(row=2, column=3)
comboxlist.current(0)  # select the first one as default

# comboxlist.bind("<<ComboboxSelected>>")
# comboxlist.pack()
# Button(text='select metafile',command=metafile).grid(row=1,column=0)   #read in the metafile
# Button(text='select target folder', command=select_folder).grid(row=1,column=1)        #select output folder
Button(text='search & create', command=search_create).grid(row=0, column=4)  # search &create the target sub-dataset
# Button(text='select by region', command=select_region).grid(row=0,column=4) #search &create the target sub-dataset
# Button(text='plot', command=).grid(row=0,column=4) #search &create the target sub-dataset
Button(text='file_select', command=file_select).grid(row=4, column=4)
# Button(text='list_id',command=list_id).grid(row=2,column=2)            #put a id list to the target sub-dataset
loop = mainloop()  # go!