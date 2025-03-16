#==================================================================
#Sub-routine to convert TRW into DBH and AABI for output and plot
#==================================================================

import rpy2
import tzlocal
import random
from rpy2.robjects import r
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import StrVector

from rpy2.robjects.packages import importr,data
from rpy2.robjects.vectors import DataFrame, StrVector
from rpy2.robjects.conversion import localconverter
from rpy2.robjects import r, pandas2ri
#import numpy as np
import pandas as pd
from pandas import *

#plot
#import ggplot
#import ggpy
from matplotlib import *
from matplotlib import pyplot
#import plotnine

#import R package
dplR = importr('dplR')
r_base = importr('base')
pandas2ri.activate()

#import function to get the site allometric relationships
from allometric_dict_species import *


def plot_allometry_species(fk,min_value,max_value,times,file_Column_Randoms,dbh_method,bark_method,output_path,region, species):
    print(f"Correction Value:",min_value,max_value,times)
    print(f"dbh_method: {dbh_method}")
    print(f"bark_method: {bark_method}")
    print(f"output_path: {output_path}")
    pyplot.rcParams['savefig.dpi'] = 300
    pyplot.rcParams['figure.dpi'] = 300
    pyplot.figure()
    
    for indexF in range(len(fk)):
        TR_input_dir = fk[indexF]
        #get the file name without direction and extension
        mm = os.path.splitext(os.path.basename(fk[indexF]))[0]
        print("mm1" + mm)
        TR_input = r['read.tucson'](TR_input_dir)
        start = r['min'](r['as.numeric'](r['rownames'](TR_input)))
        end = r['max'](r['as.numeric'](r['rownames'](TR_input)))
        #r['as.numeric'](r['max'](r['rownames'](TR_input)))
        # get observation period
        TRW = r['data.frame'](year=r['seq'](start, end, 1))
        # select only important rows ( the tree (?) or series names, e.g. "LF317s")
        all = r['names'](TR_input)

        #test for detrending
        #The heteroscedastic variance structure was stabilized using adaptive power transformation prior to detrending.
        #The age/size-related trends in the raw data were removed from
        # all series using cubic smoothing spline detrending with a 50% frequency
        # from Babst et al 2019 DOI: 10.1126/sciadv.aat4313
        #TR_powt = dplR.powt(TR_input)
        #TR_de = dplR.detrend(TR_input, method="Spline")

        #biweight robust mean (an average that is unaffected by outliers)
        #TR_de1 = dplR.chron(TR_de)
    #======================================================================================
    #start of first file processing
    #======================================================================================
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            pdf_input = rpy2.robjects.conversion.ri2py(TR_input)
            #pdf_mean = rpy2.robjects.conversion.ri2py(TR_de1)  #TRW mean
            t_start = rpy2.robjects.conversion.ri2py(start)
            t_end = rpy2.robjects.conversion.ri2py(end)
            # dataframe processing for plot
            years = range(int(t_start), int(t_end) + 1)  # get the year index in the data
            pdf_input.index = years  # put the year as the index in the data
            #pdf_mean.index = years
            pdf_input.insert(0, "Year", years)  # put years as the first column
            #pdf_mean.insert(0, "Year", years)
            pdf_input = pdf_input.drop(pdf_input.columns[0], axis=1)  # delect the first column of years
            #pdf_mean = pdf_mean.drop(pdf_mean.columns[2],axis=1)
            #pdf_mean.columns = ['Year', 'TRW_mean']

            #pdf_mean = pdf_input.mean(axis=1)
            #pdf_mean = pdf_input.mean(axis=1)
            #pdf_mean_input = DataFrame(pdf_mean)
            #pdf_mean_input.index = years  # put the year as the index in the data
            #pdf_mean_input.insert(0, "Year", years)  # put years as the first column
            #pdf_mean_input.columns = ['Year', 'TRW_mean']

            pdf_max = pdf_input.max(axis=1)
            pdf_min = pdf_input.min(axis=1)
            pdf_std = pdf_input.std(axis=1)
            pdf_c_summary = pdf_input.describe()

            # 初始化多个数据框用于存储最终结果
            final_dia = pd.DataFrame(index=pdf_input.index)
            final_bio = pd.DataFrame(index=pdf_input.index)
            final_delta_dia = pd.DataFrame(index=pdf_input.index)
            final_delta_bio = pd.DataFrame(index=pdf_input.index)
            final_diaa = pd.DataFrame(index=pdf_input.index)
            final_bioo = pd.DataFrame(index=pdf_input.index)
            final_delta_diaa = pd.DataFrame(index=pdf_input.index)
            final_delta_bioo = pd.DataFrame(index=pdf_input.index)
            final_age = pd.DataFrame(index=pdf_input.index)

            final_dia_mean = pd.DataFrame(index=pdf_input.index)
            final_bio_mean = pd.DataFrame(index=pdf_input.index)
            final_delta_dia_mean = pd.DataFrame(index=pdf_input.index)
            final_delta_bio_mean = pd.DataFrame(index=pdf_input.index)
            final_diaa_mean = pd.DataFrame(index=pdf_input.index)
            final_bioo_mean = pd.DataFrame(index=pdf_input.index)   
            final_delta_diaa_mean = pd.DataFrame(index=pdf_input.index)
            final_delta_bioo_mean = pd.DataFrame(index=pdf_input.index)
            final_age_mean = pd.DataFrame(index=pdf_input.index)

            # 初始化随机值列表
            random_values = []

            # 如果 times 大于 0，生成随机值；否则，设置默认值为 0
            if times > 0:
                random_values = [round(random.uniform(min_value, max_value), 2) for _ in range(times)]
            else:
                random_values = [0]

            print("df_input.columns = ", pdf_input.columns)
            for rand_val in random_values:
                print("rand_val = ", rand_val)
                #create output dataframes
                pdf_dia = pdf_input.copy()      #diameter df
                pdf_diaa = pdf_input.copy()     #bias corrected diameter df
                pdf_delta_dia = pdf_input.copy() #delta diameter df
                pdf_delta_diaa = pdf_input.copy() #bias corrected delta diameter df
                pdf_bio = pdf_input.copy()      #biomass df
                pdf_bioo = pdf_input.copy()      #bias corrected biomass df
                pdf_delta_bio = pdf_input.copy()  #delta biomass df
                pdf_delta_bioo = pdf_input.copy()  #bias corrected delta biomass df
                pdf_age = pdf_input.copy()
                #calculate biomass increment for each tree
                #column/tree loop
                for i in range (0,len(pdf_input.columns)):
                    #one column
                    pdf_sub = pdf_input.iloc[:,i]
                    diameter = pdf_sub.copy()
                    diameterr = pdf_sub.copy()      #bias corrected 
                    biomass = pdf_sub.copy()
                    biomasss = pdf_sub.copy()       #bias corrected
                    delta_dia = pdf_sub.copy()
                    delta_diaa = pdf_sub.copy()     #bias corrected
                    delta_bio = pdf_sub.copy()
                    delta_bioo = pdf_sub.copy()     #bias corrected
                    age = pdf_sub.copy()
                    #get the first non-NAN value and the year

                    y_start = pdf_sub.first_valid_index()
                    y_end = pdf_sub.last_valid_index()
                    length = y_end - y_start + 1
                    #year loop
                    print("y_start = ", y_start,y_end)
                    for k in range (y_start,(y_end +1)):
                        if k == y_start:

                            if pdf_sub[k] == 0:
                                pdf_sub[k] = 1e-8
                            #add random width to the start year of the tree ring width
                            #pdf_sub[k] = pdf_sub[k] + random.uniform(0, 1)
                            if times < 0:
                                pdf_sub[k] = pdf_sub[k] + file_Column_Randoms[indexF][i]
                                column_random_index += 1
                            else:
                                pdf_sub[k] = pdf_sub[k] + rand_val
                                
                            age[k] = 1
                            diameter[k] = (2 * pdf_sub[k])/10    # cm

                            if bark_method == 0:
                                diameterr[k] = diameter[k] * 0.998 + 22.3
                            else:
                                diameterr[k] = (diameter[k] ** 0.89  * 0.95)/10 + diameter[k]                    

                            # diameter estimated from rw is then corrected following the
                            # equation from Lockwood et al.,2021
                            if dbh_method == 0:
                                diameterr[k] = diameter[k] * 0.998 + 22.3
                            else:
                                #Aggregation with bark estimation
                                #equation from Zeibig-Kichas et al. 2016
                                diameterr[k] = (diameter[k] ** 0.89  * 0.95)/10 + diameter[k]
                            
                            # get biomass based allometric relationships
                            biomass[k] = allometric_dict_species(region, species, diameter[k])
                            biomasss[k] = allometric_dict_species(region, species, diameterr[k])
                            #print(biomass[k])
                            delta_dia[k] = diameter[k]
                            delta_bio[k] = biomass[k]
                            
                            delta_diaa[k] = diameterr[k]
                            delta_bioo[k] = biomasss[k]

                        
                        else:
                            if pdf_sub[k] == 0:
                                pdf_sub[k] = 1e-8
                            age[k] = age[k-1] + 1
                            diameter[k] = diameter[k-1] + (2 * pdf_sub[k])/10    # cm
                            if bark_method == 0:
                                diameterr[k] = diameter[k] * 0.998 + 22.3
                            else:
                                diameterr[k] = (diameter[k] ** 0.89  * 0.95)/10 + diameter[k]  

                            if dbh_method == 0:
                            # diameter estimated from rw is then corrected following the
                            # equation from Lockwood et al.,2021
                                diameterr[k] = diameter[k] * 0.998 + 22.3
                            else:
                                #Aggregation with bark estimation
                                #equation from Zeibig-Kichas et al. 2016
                                diameterr[k] = (diameter[k] ** 0.89  * 0.95)/10 + diameter[k]
                            #if (k == 134):
                            #    print(pdf_sub[k])
                            #    print(diameter[k])
                            #print(diameter[k-1])
                            #get biomass based allometric relationships
                            biomass[k] = allometric_dict_species(region, species,diameter[k])
                            biomasss[k] = allometric_dict_species(region, species, diameterr[k])
                            #print(biomass[k])
                            delta_dia[k] = diameter[k] - diameter[k - 1]
                            delta_bio[k] = biomass[k] - biomass[k-1]
                            
                            delta_diaa[k] = diameterr[k] - diameterr[k - 1]
                            delta_bioo[k] = biomasss[k] - biomasss[k-1]

                            #print(k)
                            #print(pdf_sub[k])
                            #print(i)

                        count = k - pdf_sub.index[0]
                        pdf_dia.iloc[count,i] = diameter[k]
                        pdf_delta_dia.iloc[count,i] = delta_dia[k]
                        pdf_bio.iloc[count,i] = biomass[k]  # biomass df
                        pdf_delta_bio.iloc[count,i] = delta_bio[k]  # delta biomass df
                        pdf_diaa.iloc[count,i] = diameterr[k]
                        pdf_delta_diaa.iloc[count,i] = delta_diaa[k]
                        pdf_bioo.iloc[count,i] = biomasss[k]  # biomass df
                        pdf_delta_bioo.iloc[count,i] = delta_bioo[k]  # delta biomass df
                        pdf_age.iloc[count,i] = age[k]

                #Get the mean values using biweight robust mean
                #convert to r df first
                r_pdf_dia = rpy2.robjects.conversion.py2ri(pdf_dia)
                r_pdf_delta_dia = rpy2.robjects.conversion.py2ri(pdf_delta_dia)
                r_pdf_bio = rpy2.robjects.conversion.py2ri(pdf_bio)
                r_pdf_delta_bio = rpy2.robjects.conversion.py2ri(pdf_delta_bio)
                r_pdf_diaa = rpy2.robjects.conversion.py2ri(pdf_diaa)
                r_pdf_delta_diaa = rpy2.robjects.conversion.py2ri(pdf_delta_diaa)
                r_pdf_bioo = rpy2.robjects.conversion.py2ri(pdf_bioo)
                r_pdf_delta_bioo = rpy2.robjects.conversion.py2ri(pdf_delta_bioo)
                r_pdf_age = rpy2.robjects.conversion.py2ri(pdf_age)

                r_pdf_dia_mean = dplR.chron(r_pdf_dia)
                r_pdf_delta_dia_mean = dplR.chron(r_pdf_delta_dia)
                r_pdf_bio_mean = dplR.chron(r_pdf_bio)
                r_pdf_delta_bio_mean = dplR.chron(r_pdf_delta_bio)
                r_pdf_diaa_mean = dplR.chron(r_pdf_diaa)
                r_pdf_delta_diaa_mean = dplR.chron(r_pdf_delta_diaa)
                r_pdf_bioo_mean = dplR.chron(r_pdf_bioo)
                r_pdf_delta_bioo_mean = dplR.chron(r_pdf_delta_bioo)
                r_pdf_age_mean = dplR.chron(r_pdf_age)

                pdf_dia_mean = rpy2.robjects.conversion.ri2py(r_pdf_dia_mean)
                pdf_delta_dia_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_dia_mean)
                pdf_bio_mean = rpy2.robjects.conversion.ri2py(r_pdf_bio_mean)
                pdf_delta_bio_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_bio_mean)
                pdf_diaa_mean = rpy2.robjects.conversion.ri2py(r_pdf_diaa_mean)
                pdf_delta_diaa_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_diaa_mean)
                pdf_bioo_mean = rpy2.robjects.conversion.ri2py(r_pdf_bioo_mean)
                pdf_delta_bioo_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_bioo_mean)
                pdf_age_mean = rpy2.robjects.conversion.ri2py(r_pdf_age_mean)

                pdf_dia_mean.insert(0, "Year", years)
                #pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_dia_mean.columns = ['Year', 'dia_mean','samp.depth']

                pdf_delta_dia_mean.insert(0, "Year", years)
                #pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_delta_dia_mean.columns = ['Year', 'd_dia_mean','samp.depth']

                pdf_bio_mean.insert(0, "Year", years)
                #pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_bio_mean.columns = ['Year', 'bio_mean','samp.depth']

                pdf_delta_bio_mean.insert(0, "Year", years)
                #pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_delta_bio_mean.columns = ['Year', 'd_bio_mean','samp.depth']

                pdf_diaa_mean.insert(0, "Year", years)
                # pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_diaa_mean.columns = ['Year', 'dia_mean', 'samp.depth']

                pdf_delta_diaa_mean.insert(0, "Year", years)
                # pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_delta_diaa_mean.columns = ['Year', 'd_dia_mean', 'samp.depth']

                pdf_bioo_mean.insert(0, "Year", years)
                # pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_bioo_mean.columns = ['Year', 'bio_mean', 'samp.depth']

                pdf_delta_bioo_mean.insert(0, "Year", years)
                # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
                pdf_delta_bioo_mean.columns = ['Year', 'd_bio_mean', 'samp.depth']

                pdf_age_mean.insert(0, "Year", years)
                pdf_age_mean.columns = ['Year','age','samp.depth']
                #simple mean values
                #pdf_dia_mean = pdf_dia.iloc[:,1:(len(pdf_dia.columns)+1)].mean(1)
                #pdf_delta_dia_mean = pdf_delta_dia.iloc[:,1:(len(pdf_delta_dia.columns)+1)].mean(1)
                #pdf_bio_mean = pdf_bio.iloc[:,1:(len(pdf_bio.columns)+1)].mean(1)
                #pdf_delta_bio_mean = pdf_delta_bio.iloc[:,1:(len(pdf_delta_bio.columns)+1)].mean(1)
                
                if times > 0:
                    # 更新列名
                    pdf_dia.columns = [f"{pdf_dia.columns[0]}_{rand_val}"] + list(pdf_dia.columns[1:])
                    pdf_bio.columns = [f"{pdf_bio.columns[0]}_{rand_val}"] + list(pdf_bio.columns[1:])
                    pdf_delta_dia.columns = [f"{pdf_delta_dia.columns[0]}_{rand_val}"] + list(pdf_delta_dia.columns[1:])
                    pdf_delta_bio.columns = [f"{pdf_delta_bio.columns[0]}_{rand_val}"] + list(pdf_delta_bio.columns[1:])
                    pdf_diaa.columns = [f"{pdf_diaa.columns[0]}_{rand_val}"] + list(pdf_diaa.columns[1:])
                    pdf_bioo.columns = [f"{pdf_bioo.columns[0]}_{rand_val}"] + list(pdf_bioo.columns[1:])
                    pdf_delta_diaa.columns = [f"{pdf_delta_diaa.columns[0]}_{rand_val}"] + list(pdf_delta_diaa.columns[1:])
                    pdf_delta_bioo.columns = [f"{pdf_delta_bioo.columns[0]}_{rand_val}"] + list(pdf_delta_bioo.columns[1:])
                    pdf_age.columns = [f"{pdf_age.columns[0]}_{rand_val}"] + list(pdf_age.columns[1:])            

                    # 给第二列的列名追加上对应的随机值 {rand_val}
                    pdf_dia_mean.columns = [pdf_dia_mean.columns[0], f"{pdf_dia_mean.columns[1]}_{rand_val}"] + list(pdf_dia_mean.columns[2:])
                    pdf_delta_dia_mean.columns = [pdf_delta_dia_mean.columns[0], f"{pdf_delta_dia_mean.columns[1]}_{rand_val}"] + list(pdf_delta_dia_mean.columns[2:])
                    pdf_bio_mean.columns = [pdf_bio_mean.columns[0], f"{pdf_bio_mean.columns[1]}_{rand_val}"] + list(pdf_bio_mean.columns[2:])
                    pdf_delta_bio_mean.columns = [pdf_delta_bio_mean.columns[0], f"{pdf_delta_bio_mean.columns[1]}_{rand_val}"] + list(pdf_delta_bio_mean.columns[2:])
                    pdf_diaa_mean.columns = [pdf_diaa_mean.columns[0], f"{pdf_diaa_mean.columns[1]}_{rand_val}"] + list(pdf_diaa_mean.columns[2:])
                    pdf_delta_diaa_mean.columns = [pdf_delta_diaa_mean.columns[0], f"{pdf_delta_diaa_mean.columns[1]}_{rand_val}"] + list(pdf_delta_diaa_mean.columns[2:])
                    pdf_bioo_mean.columns = [pdf_bioo_mean.columns[0], f"{pdf_bioo_mean.columns[1]}_{rand_val}"] + list(pdf_bioo_mean.columns[2:])
                    pdf_delta_bioo_mean.columns = [pdf_delta_bioo_mean.columns[0], f"{pdf_delta_bioo_mean.columns[1]}_{rand_val}"] + list(pdf_delta_bioo_mean.columns[2:])
                    pdf_age_mean.columns = [pdf_age_mean.columns[0], f"{pdf_age_mean.columns[1]}_{rand_val}"] + list(pdf_age_mean.columns[2:])

                # 在合并之前打印数据框的内容和形状
                print("pdf_dia shape:", pdf_dia.shape)
                print(pdf_dia.head())

                # 将结果合并到最终数据框
                final_dia = pd.concat([final_dia, pdf_dia], axis=1)
                final_bio = pd.concat([final_bio, pdf_bio], axis=1)
                final_delta_dia = pd.concat([final_delta_dia, pdf_delta_dia], axis=1)
                final_delta_bio = pd.concat([final_delta_bio, pdf_delta_bio], axis=1)
                final_diaa = pd.concat([final_diaa, pdf_diaa], axis=1)
                final_bioo = pd.concat([final_bioo, pdf_bioo], axis=1)
                final_delta_diaa = pd.concat([final_delta_diaa, pdf_delta_diaa], axis=1)
                final_delta_bioo = pd.concat([final_delta_bioo, pdf_delta_bioo], axis=1)
                final_age = pd.concat([final_age, pdf_age], axis=1)
                
                print("pdf_dia_mean shape:", pdf_dia_mean.shape)
                print(pdf_dia_mean.head())

                # Concatenate mean data
                if final_dia_mean.empty:
                    final_dia_mean = pdf_dia_mean
                else:
                    # Extract the third column and insert it before the last column
                    new_col = pdf_dia_mean.iloc[:, 1]
                    final_dia_mean.insert(len(final_dia_mean.columns) - 1, new_col.name, new_col)

                if final_delta_dia_mean.empty:
                    final_delta_dia_mean = pdf_delta_dia_mean
                else:
                    new_col = pdf_delta_dia_mean.iloc[:, 1]
                    final_delta_dia_mean.insert(len(final_delta_dia_mean.columns) - 1, new_col.name, new_col)

                if final_bio_mean.empty:
                    final_bio_mean = pdf_bio_mean
                else:
                    new_col = pdf_bio_mean.iloc[:, 1]
                    final_bio_mean.insert(len(final_bio_mean.columns) - 1, new_col.name, new_col)

                if final_delta_bio_mean.empty:
                    final_delta_bio_mean = pdf_delta_bio_mean
                else:
                    new_col = pdf_delta_bio_mean.iloc[:, 1]
                    final_delta_bio_mean.insert(len(final_delta_bio_mean.columns) - 1, new_col.name, new_col)

                if final_diaa_mean.empty:
                    final_diaa_mean = pdf_diaa_mean
                else:
                    new_col = pdf_diaa_mean.iloc[:, 1]
                    final_diaa_mean.insert(len(final_diaa_mean.columns) - 1, new_col.name, new_col)

                if final_delta_diaa_mean.empty:
                    final_delta_diaa_mean = pdf_delta_diaa_mean
                else:
                    new_col = pdf_delta_diaa_mean.iloc[:, 1]
                    final_delta_diaa_mean.insert(len(final_delta_diaa_mean.columns) - 1, new_col.name, new_col)

                if final_bioo_mean.empty:
                    final_bioo_mean = pdf_bioo_mean
                else:
                    new_col = pdf_bioo_mean.iloc[:, 1]
                    final_bioo_mean.insert(len(final_bioo_mean.columns) - 1, new_col.name, new_col)

                if final_delta_bioo_mean.empty:
                    final_delta_bioo_mean = pdf_delta_bioo_mean
                else:
                    new_col = pdf_delta_bioo_mean.iloc[:, 1]
                    final_delta_bioo_mean.insert(len(final_delta_bioo_mean.columns) - 1, new_col.name, new_col)

                if final_age_mean.empty:
                    final_age_mean = pdf_age_mean
                else:
                    new_col = pdf_age_mean.iloc[:, 1]
                    final_age_mean.insert(len(final_age_mean.columns) - 1, new_col.name, new_col)

            if bark_method == 0:
                a = 1
            else:
                a = 0

            initbias0 = random_values[0]   
            if dbh_method == 0:
                name_dia = mm + "_dia_"+ str(round(initbias0,3)) +".csv"
                name_dia_mean = mm + "_dia_mean_"+ str(round(initbias0,3)) + ".csv"
                name_bio = mm + "_bio_"+ str(round(initbias0,3)) + ".csv"
                name_bio_mean = mm + "_bio_mean_"+ str(round(initbias0,3)) + ".csv"

                name_delta_dia = mm + "_delta_dia_"+ str(round(initbias0,3)) + ".csv"
                name_delta_dia_mean = mm + "_delta_dia_mean_"+ str(round(initbias0,3)) +".csv"
                name_delta_bio = mm + "_delta_bio_"+ str(round(initbias0,3)) +".csv"
                name_delta_bio_mean = mm + "_delta_bio_mean_"+ str(round(initbias0,3)) +".csv"

                name_diaa = mm + "_dia_bias_corr_"+ str(round(initbias0,3)) + "_L.csv"
                name_diaa_mean = mm + "_dia_mean_bias_corr_" + str(round(initbias0,3)) + "_L.csv"
                name_bioo = mm + "_bio_bias_corr_" + str(round(initbias0,3)) + "_L.csv"
                name_bioo_mean = mm + "_bio_mean_bias_corr_" + str(round(initbias0,3)) + "_L.csv"

                name_delta_diaa = mm + "_delta_dia_bias_corr_" + str(round(initbias0,3)) + "_L.csv"
                name_delta_diaa_mean = mm + "_delta_dia_mean_bias_corr_" + str(round(initbias0,3)) +"_L.csv"
                name_delta_bioo = mm + "_delta_bio_bias_corr_" + str(round(initbias0,3)) + "_L.csv"
                name_delta_bioo_mean = mm + "_delta_bio_mean_bias_corr_" + str(round(initbias0,3)) +"_L.csv"

                name_age = mm + "_age.csv"
                name_age_mean = mm + "_age_mean.csv"
            else:
                name_dia = mm + "_dia_"+ str(round(initbias0,3)) +".csv"
                name_dia_mean = mm + "_dia_mean_"+ str(round(initbias0,3)) + ".csv"
                name_bio = mm + "_bio_"+ str(round(initbias0,3)) + ".csv"
                name_bio_mean = mm + "_bio_mean_"+ str(round(initbias0,3)) + ".csv"

                name_delta_dia = mm + "_delta_dia_"+ str(round(initbias0,3)) + ".csv"
                name_delta_dia_mean = mm + "_delta_dia_mean_"+ str(round(initbias0,3)) +".csv"
                name_delta_bio = mm + "_delta_bio_"+ str(round(initbias0,3)) +".csv"
                name_delta_bio_mean = mm + "_delta_bio_mean_"+ str(round(initbias0,3)) +".csv"

                name_diaa = mm + "_dia_bias_corr_"+ str(round(initbias0,3)) + "_N.csv"
                name_diaa_mean = mm + "_dia_mean_bias_corr_" + str(round(initbias0,3)) + "_N.csv"
                name_bioo = mm + "_bio_bias_corr_" + str(round(initbias0,3)) + "_N.csv"
                name_bioo_mean = mm + "_bio_mean_bias_corr_" + str(round(initbias0,3)) + "_N.csv"

                name_delta_diaa = mm + "_delta_dia_bias_corr_" + str(round(initbias0,3)) + "_N.csv"
                name_delta_diaa_mean = mm + "_delta_dia_mean_bias_corr_" + str(round(initbias0,3)) +"_N.csv"
                name_delta_bioo = mm + "_delta_bio_bias_corr_" + str(round(initbias0,3)) + "_N.csv"
                name_delta_bioo_mean = mm + "_delta_bio_mean_bias_corr_" + str(round(initbias0,3)) +"_N.csv"

                name_age = mm + "_age.csv"
                name_age_mean = mm + "_age_mean.csv"
                #pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
                #pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
                

            output_dia = os.path.join(output_path, name_dia)
            final_dia.to_csv(output_dia, sep=',', na_rep="-999")
            
            output_dia_mean = os.path.join(output_path, name_dia_mean)
            final_dia_mean.to_csv(output_dia_mean, sep=',', na_rep="-999")

            output_bio = os.path.join(output_path, name_bio)
            final_bio.to_csv(output_bio, sep=',', na_rep="-999")

            output_bio_mean = os.path.join(output_path, name_bio_mean)
            final_bio_mean.to_csv(output_bio_mean, sep=',', na_rep="-999")

            output_delta_dia = os.path.join(output_path, name_delta_dia)
            final_delta_dia.to_csv(output_delta_dia, sep=',', na_rep="-999")

            output_delta_dia_mean = os.path.join(output_path, name_delta_dia_mean)
            final_delta_dia_mean.to_csv(output_delta_dia_mean, sep=',', na_rep="-999")
            
            output_delta_bio = os.path.join(output_path, name_delta_bio)
            final_delta_bio.to_csv(output_delta_bio, sep=',', na_rep="-999")

            output_delta_bio_mean = os.path.join(output_path, name_delta_bio_mean)
            final_delta_bio_mean.to_csv(output_delta_bio_mean, sep=',', na_rep="-999")
            
            output_diaa = os.path.join(output_path, name_diaa)
            final_diaa.to_csv(output_diaa, sep=',', na_rep="-999")

            output_diaa_mean = os.path.join(output_path, name_diaa_mean)
            final_diaa_mean.to_csv(output_diaa_mean, sep=',', na_rep="-999")

            output_bioo = os.path.join(output_path, name_bioo)
            final_bioo.to_csv(output_bioo, sep=',', na_rep="-999")

            output_bioo_mean = os.path.join(output_path, name_bioo_mean)
            final_bioo_mean.to_csv(output_bioo_mean, sep=',', na_rep="-999")

            output_delta_diaa = os.path.join(output_path, name_delta_diaa)
            final_delta_diaa.to_csv(output_delta_diaa, sep=',', na_rep="-999")

            output_delta_diaa_mean = os.path.join(output_path, name_delta_diaa_mean)
            final_delta_diaa_mean.to_csv(output_delta_diaa_mean, sep=',', na_rep="-999")

            output_delta_bioo = os.path.join(output_path, name_delta_bioo)
            final_delta_bioo.to_csv(output_delta_bioo, sep=',', na_rep="-999")

            output_delta_bioo_mean = os.path.join(output_path, name_delta_bioo_mean) 
            final_delta_bioo_mean.to_csv(output_delta_bioo_mean, sep=',', na_rep="-999")
            

            #pdf_mean.plot(label='TR mean')
            #pdf_upper.plot(label='upper error')
            #pdf_lower.plot(label='lower error')
            #remove the first year for the delta_bio output, as no past year exists
            final_delta_bioo_mean1 = final_delta_bioo_mean[1:]
            #set up for plot
            #pyplot.plot(final_delta_bioo_mean1['Year'],final_elta_bioo_mean1['d_bio_mean'],label = mm)

            # 获取更新后的列名
            d_bio_mean_col = [col for col in final_delta_bioo_mean1.columns if col.startswith('d_bio_mean_')][0]

            # 绘制图形
            pyplot.plot(final_delta_bioo_mean1['Year'], final_delta_bioo_mean1[d_bio_mean_col], label=mm)

            #final_delta_bioo_mean["d_bio_mean"] .plot(label=mm)

    print('bingo')
    pyplot.legend(loc='upper left')
    pyplot.ylabel('AABI (kgC $tree^{-1} year^{-1}$)')
    pyplot.xlabel('year')
    pyplot.show()
#====================================================================================
#end of first file processing
#====================================================================================


#====================================================================================
#start of the processing of the rest files
#====================================================================================
'''
    for i in range(1, len(fk)):
        TR_input_dir = fk[i]
        TR_input = r['read.tucson'](TR_input_dir)
        start = r['min'](r['as.numeric'](r['rownames'](TR_input)))
        end = r['max'](r['as.numeric'](r['rownames'](TR_input)))
        # get observation period
        TRW = r['data.frame'](year=r['seq'](start, end, 1))
        # select only important rows ( the tree (?) or series names, e.g. "LF317s")
        all = r['names'](TR_input)

        # The heteroscedastic variance structure was stabilized using adaptive power transformation prior to detrending.
        # The age/size-related trends in the raw data were removed from
        # all series using cubic smoothing spline detrending with a 50% frequency
        # from Babst et al 2019 DOI: 10.1126/sciadv.aat4313
        #TR_powt = dplR.powt(TR_input)
        #TR_de = dplR.detrend(TR_input, method="Spline")
        # TR_de1 = dplR.chron(TR_de, prefix="CAM")
        # print("test")
        # print(TR_de1)

        # biweight robust mean (an average that is unaffected by outliers)
        #TR_de1 = dplR.chron(TR_de)

        #get the file name without direct and file type Yizhao 2019/12/23
        mm = os.path.splitext(os.path.basename(fk[i]))[0]
        print("mm2"+ mm)
        with localconverter(rpy2.robjects.default_converter + pandas2ri.converter):
            pdf_input1 = rpy2.robjects.conversion.ri2py(TR_input)
            #pdf_mean1 = rpy2.robjects.conversion.ri2py(TR_de1)  #TRW mean
            t_start = rpy2.robjects.conversion.ri2py(start)
            t_end = rpy2.robjects.conversion.ri2py(end)
            # dataframe processing for plot
            years = range(int(t_start), int(t_end) + 1)  # get the year index in the data
            pdf_input1.index = years  # put the year as the index in the data
            #pdf_mean1.index = years
            pdf_input1.insert(0, "Year", years)  # put years as the first column
            #pdf_mean1.insert(0, "Year", years)
            pdf_input1 = pdf_input1.drop(pdf_input1.columns[0], axis=1)  # delect the first column of years
            #pdf_mean1 = pdf_mean1.drop(pdf_mean1.columns[2], axis=1)
            #pdf_mean1.columns = ['Year', 'TRW_mean']


            # pdf_mean1 = pdf_input1.mean(axis=1)
            # pdf_mean1_input = DataFrame(pdf_mean1)
            # pdf_mean1_input.index = years  # put the year as the index in the data
            # pdf_mean1_input.insert(0, "Year", years)  # put years as the first column
            # pdf_mean1_input.columns = ['Year','TRW_mean']

            pdf_max1 = pdf_input1.max(axis=1)
            pdf_min1 = pdf_input1.min(axis=1)
            pdf_std1 = pdf_input1.std(axis=1)
            pdf_c_summary1 = pdf_input1.describe()

            # create
            pdf_dia1 = pdf_input1.copy()  # diameter df
            pdf_dia2 = pdf_input1.copy()  # bias corrected diamter df
            pdf_delta_dia1 = pdf_input1.copy()  # delta diameter df
            pdf_delta_dia2 = pdf_input1.copy()  # bias corrected delta diameter df
            pdf_bio1 = pdf_input1.copy()  # biomass df
            pdf_bio2 = pdf_input1.copy()  # bias corrected biomass df
            pdf_delta_bio1 = pdf_input1.copy()  # delta biomass df
            pdf_delta_bio2 = pdf_input1.copy()  # bias corrected delta biomass df
            pdf_age1 = pdf_input1.copy()
            # calculate biomass increment for each tree
            # column loop
            for i in range(0, len(pdf_input1.columns)):
                # one column
                pdf_sub1 = pdf_input1.iloc[:, i]
                diameter1 = pdf_sub1.copy()
                diameter2 = pdf_sub1.copy()
                biomass1 = pdf_sub1.copy()
                biomass2 = pdf_sub1.copy()
                delta_dia1 = pdf_sub1.copy()
                delta_dia2 = pdf_sub1.copy()
                delta_bio1 = pdf_sub1.copy()
                delta_bio2 = pdf_sub1.copy()
                age1 = pdf_sub1.copy()
                # get the first non-NAN value and the year

                y_start1 = pdf_sub1.first_valid_index()
                y_end1 = pdf_sub1.last_valid_index()
                length1 = y_end1 - y_start1 + 1

                # year loop
                for k in range(y_start1, (y_end1 + 1)):
                    if k == y_start1:

                        if pdf_sub1[k] == 0:
                            pdf_sub1[k] = 1e-8
                        #add random width to the start year of the tree ring width
                        #pdf_sub1[k] = pdf_sub1[k] + random.uniform(0, 1)
                        pdf_sub1[k] = pdf_sub1[k] + initbias[i]
                        age1[k] = 1
                        diameter1[k] = (2 * pdf_sub1[k]) / 10  # cm
                        if bark_method == 0:
                            diameter2[k] = diameter1[k] * 0.998 + 22.3
                        else:
                            diameter2[k] = (diameter1[k] ** 0.89  * 0.95)/10 + diameter1[k]

                        #diameter estimated from rw is then corrected following the
                        #equation from Lockwood et al.,2021
                        if dbh_method == 0:
                            diameter2[k] = diameter1[k] * 0.998 + 22.3
                        else: 
                        #Aggregation with bark estimation
                        #equation from Zeibig-Kichas et al. 2016
                            diameter2[k] = (diameter1[k] ** 0.89  * 0.95)/10 + diameter1[k]
                        # get biomass based allometric relationships
                        biomass1[k] = allometric_dict_species(region, species, diameter1[k])
                        biomass2[k] = allometric_dict_species(region, species, diameter2[k])
                        # print(biomass[k])
                        delta_dia1[k] = diameter1[k]
                        delta_bio1[k] = biomass1[k]

                        delta_dia2[k] = diameter2[k]
                        delta_bio2[k] = biomass2[k]

                    else:
                        if pdf_sub1[k] == 0:
                            pdf_sub1[k] = 1e-8
                        age1[k] = age1[k-1] + 1
                        diameter1[k] = diameter1[k - 1] + (2 * pdf_sub1[k]) / 10  # cm
                        if bark_method == 0:
                            diameter2[k] = diameter1[k] * 0.998 + 22.3
                        else:
                            diameter2[k] = (diameter1[k] ** 0.89  * 0.95)/10 + diameter1[k]

                        #diameter estimated from rw is then corrected following the
                        #equation from Lockwood et al.,2021
                        if dbh_method ==0:
                            diameter2[k] = diameter1[k] * 0.998 + 22.3
                        else:
                        #Aggregation with bark estimation
                        #equation from Zeibig-Kichas et al. 2016
                            diameter2[k] = (diameter1[k] ** 0.89  * 0.95)/10 + diameter1[k]
                        # get biomass based allometric relationships
                        biomass1[k] = allometric_dict_species(region, species, diameter1[k])
                        biomass2[k] = allometric_dict_species(region, species, diameter2[k])
                        # print(biomass[k])
                        delta_dia1[k] = diameter1[k] - diameter1[k - 1]
                        delta_bio1[k] = biomass1[k] - biomass1[k - 1]

                        delta_dia2[k] = diameter2[k] - diameter2[k - 1]
                        delta_bio2[k] = biomass2[k] - biomass2[k - 1]


                    count1 = k - pdf_sub1.index[0]
                    pdf_dia1.iloc[count1, i] = diameter1[k]
                    pdf_delta_dia1.iloc[count1, i] = delta_dia1[k]
                    pdf_bio1.iloc[count1, i] = biomass1[k]  # biomass df
                    pdf_delta_bio1.iloc[count1, i] = delta_bio1[k]  # delta biomass df
                    pdf_dia2.iloc[count1, i] = diameter2[k]
                    pdf_delta_dia2.iloc[count1, i] = delta_dia2[k]
                    pdf_bio2.iloc[count1, i] = biomass2[k]  # biomass df
                    pdf_delta_bio2.iloc[count1, i] = delta_bio2[k]  # delta biomass df
                    pdf_age1.iloc[count1,i] = age1[k]
            # Get the mean values using biweight robust mean
            # convert to r df first
            r_pdf_dia1 = rpy2.robjects.conversion.py2ri(pdf_dia1)
            r_pdf_delta_dia1 = rpy2.robjects.conversion.py2ri(pdf_delta_dia1)
            r_pdf_bio1 = rpy2.robjects.conversion.py2ri(pdf_bio1)
            r_pdf_delta_bio1 = rpy2.robjects.conversion.py2ri(pdf_delta_bio1)
            r_pdf_dia2 = rpy2.robjects.conversion.py2ri(pdf_dia2)
            r_pdf_delta_dia2 = rpy2.robjects.conversion.py2ri(pdf_delta_dia2)
            r_pdf_bio2 = rpy2.robjects.conversion.py2ri(pdf_bio2)
            r_pdf_delta_bio2 = rpy2.robjects.conversion.py2ri(pdf_delta_bio2)
            r_pdf_age1 = rpy2.robjects.conversion.py2ri(pdf_age1)

            r_pdf_dia_mean1 = dplR.chron(r_pdf_dia1)
            r_pdf_delta_dia_mean1 = dplR.chron(r_pdf_delta_dia1)
            r_pdf_bio_mean1 = dplR.chron(r_pdf_bio1)
            r_pdf_delta_bio_mean1 = dplR.chron(r_pdf_delta_bio1)
            r_pdf_dia_mean2 = dplR.chron(r_pdf_dia2)
            r_pdf_delta_dia_mean2 = dplR.chron(r_pdf_delta_dia2)
            r_pdf_bio_mean2 = dplR.chron(r_pdf_bio2)
            r_pdf_delta_bio_mean2 = dplR.chron(r_pdf_delta_bio2)
            r_pdf_age_mean1 = dplR.chron(r_pdf_age1)

            pdf_dia_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_dia_mean1)
            pdf_delta_dia_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_delta_dia_mean1)
            pdf_bio_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_bio_mean1)
            pdf_delta_bio_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_delta_bio_mean1)
            pdf_dia_mean2 = rpy2.robjects.conversion.ri2py(r_pdf_dia_mean2)
            pdf_delta_dia_mean2 = rpy2.robjects.conversion.ri2py(r_pdf_delta_dia_mean2)
            pdf_bio_mean2 = rpy2.robjects.conversion.ri2py(r_pdf_bio_mean2)
            pdf_delta_bio_mean2 = rpy2.robjects.conversion.ri2py(r_pdf_delta_bio_mean2)
            pdf_age_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_age_mean1)

            # Get the mean values
            #pdf_dia_mean1 = pdf_dia1.iloc[:, 1:(len(pdf_dia1.columns) + 1)].mean(1)
            #pdf_delta_dia_mean1 = pdf_delta_dia1.iloc[:, 1:(len(pdf_delta_dia1.columns) + 1)].mean(1)
            #pdf_bio_mean1 = pdf_bio1.iloc[:, 1:(len(pdf_bio1.columns) + 1)].mean(1)
            #pdf_delta_bio_mean1 = pdf_delta_bio1.iloc[:, 1:(len(pdf_delta_bio1.columns) + 1)].mean(1)

            pdf_dia_mean1.insert(0, "Year", years)
            # pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_dia_mean1.columns = ['Year', 'dia_mean', 'samp.depth']

            pdf_delta_dia_mean1.insert(0, "Year", years)
            # pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_delta_dia_mean1.columns = ['Year', 'd_dia_mean', 'samp.depth']

            pdf_bio_mean1.insert(0, "Year", years)
            # pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_bio_mean1.columns = ['Year', 'bio_mean', 'samp.depth']

            pdf_delta_bio_mean1.insert(0, "Year", years)
            # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_delta_bio_mean1.columns = ['Year', 'd_bio_mean', 'samp.depth']
            
            pdf_dia_mean2.insert(0, "Year", years)
            # pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_dia_mean2.columns = ['Year', 'dia_mean', 'samp.depth']

            pdf_delta_dia_mean2.insert(0, "Year", years)
            # pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_delta_dia_mean2.columns = ['Year', 'd_dia_mean', 'samp.depth']

            pdf_bio_mean2.insert(0, "Year", years)
            # pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_bio_mean2.columns = ['Year', 'bio_mean', 'samp.depth']

            pdf_delta_bio_mean2.insert(0, "Year", years)
            # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_delta_bio_mean2.columns = ['Year', 'd_bio_mean', 'samp.depth']

            pdf_age_mean1.insert(0, "Year", years)
            # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_age_mean1.columns = ['Year', 'age_mean', 'samp.depth']
        
        if bark_method == 0:
            a = 0
        else:
            a = 1
        
        if dbh_method == 0:
            name_dia1 = mm + "_dia_"+ str(round(initbias[i],3)) +".csv"
            name_dia_mean1 = mm + "_dia_mean_"+ str(round(initbias[i],3)) + ".csv"
            name_bio1 = mm + "_bio_"+ str(round(initbias[i],3)) + ".csv"
            name_bio_mean1 = mm + "_bio_mean_"+ str(round(initbias[i],3)) + ".csv"

            name_delta_dia1 = mm + "_delta_dia_"+ str(round(initbias[i],3)) + ".csv"
            name_delta_dia_mean1 = mm + "_delta_dia_mean_"+ str(round(initbias[i],3)) +".csv"
            name_delta_bio1 = mm + "_delta_bio_"+ str(round(initbias[i],3)) +".csv"
            name_delta_bio_mean1 = mm + "_delta_bio_mean_"+ str(round(initbias[i],3)) +".csv"

            name_dia2 = mm + "_dia_bias_corr_"+ str(round(initbias[i],3)) + "_L.csv"
            name_dia_mean2 = mm + "_dia_mean_bias_corr_" + str(round(initbias[i],3)) + "_L.csv"
            name_bio2 = mm + "_bio_bias_corr_" + str(round(initbias[i],3)) + "_L.csv"
            name_bio_mean2 = mm + "_bio_mean_bias_corr_" + str(round(initbias[i],3)) + "_L.csv"

            name_delta_dia2 = mm + "_delta_dia_bias_corr_" + str(round(initbias[i],3)) + "_L.csv"
            name_delta_dia_mean2 = mm + "_delta_dia_mean_bias_corr_" + str(round(initbias[i],3)) +"_L.csv"
            name_delta_bio2 = mm + "_delta_bio_bias_corr_" + str(round(initbias[i],3)) + "_L.csv"
            name_delta_bio_mean2 = mm + "_delta_bio_mean_bias_corr_" + str(round(initbias[i],3)) +"_L.csv"

            name_age = mm + "_age.csv"
            name_age_mean = mm + "_age_mean.csv"
        else:
            name_dia1 = mm + "_dia_"+ str(round(initbias[i],3)) +".csv"
            name_dia_mean1 = mm + "_dia_mean_"+ str(round(initbias[i],3)) + ".csv"
            name_bio1 = mm + "_bio_"+ str(round(initbias[i],3)) + ".csv"
            name_bio_mean1 = mm + "_bio_mean_"+ str(round(initbias[i],3)) + ".csv"

            name_delta_dia1 = mm + "_delta_dia_"+ str(round(initbias[i],3)) + ".csv"
            name_delta_dia_mean1 = mm + "_delta_dia_mean_"+ str(round(initbias[i],3)) +".csv"
            name_delta_bio1 = mm + "_delta_bio_"+ str(round(initbias[i],3)) +".csv"
            name_delta_bio_mean1 = mm + "_delta_bio_mean_"+ str(round(initbias[i],3)) +".csv"

            name_dia2 = mm + "_dia_bias_corr_"+ str(round(initbias[i],3)) + "_N.csv"
            name_dia_mean2 = mm + "_dia_mean_bias_corr_" + str(round(initbias[i],3)) + "_N.csv"
            name_bio2 = mm + "_bio_bias_corr_" + str(round(initbias[i],3)) + "_N.csv"
            name_bio_mean2 = mm + "_bio_mean_bias_corr_" + str(round(initbias[i],3)) + "_N.csv"

            name_delta_dia2 = mm + "_delta_dia_bias_corr_" + str(round(initbias[i],3)) + "_N.csv"
            name_delta_dia_mean2 = mm + "_delta_dia_mean_bias_corr_" + str(round(initbias[i],3)) +"_N.csv"
            name_delta_bio2 = mm + "_delta_bio_bias_corr_" + str(round(initbias[i],3)) + "_N.csv"
            name_delta_bio_mean2 = mm + "_delta_bio_mean_bias_corr_" + str(round(initbias[i],3)) +"_N.csv"


            # pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
            # pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
            #pdf_dia1.to_csv(name_dia1, sep=',', na_rep="-999")
            #pdf_dia_mean1.to_csv(name_dia_mean1, sep=',', na_rep="-999")
            #pdf_bio1.to_csv(name_bio1, sep=',', na_rep="-999")
            #pdf_bio_mean1.to_csv(name_bio_mean1, sep=',', na_rep="-999")

            #pdf_delta_dia1.to_csv(name_delta_dia1, sep=',', na_rep="-999")
            #pdf_delta_dia_mean1.to_csv(name_delta_dia_mean1, sep=',', na_rep="-999")
            #pdf_delta_bio1.to_csv(name_delta_bio1, sep=',', na_rep="-999")
            #pdf_delta_bio_mean1.to_csv(name_delta_bio_mean1, sep=',', na_rep="-999")

            #pdf_dia2.to_csv(name_dia2, sep=',', na_rep="-999")
            #pdf_dia_mean2.to_csv(name_dia_mean2, sep=',', na_rep="-999")
            #pdf_bio2.to_csv(name_bio2, sep=',', na_rep="-999")
            #pdf_bio_mean2.to_csv(name_bio_mean2, sep=',', na_rep="-999")

            #pdf_delta_dia2.to_csv(name_delta_dia2, sep=',', na_rep="-999")
            #pdf_delta_dia_mean2.to_csv(name_delta_dia_mean2, sep=',', na_rep="-999")
            #pdf_delta_bio2.to_csv(name_delta_bio2, sep=',', na_rep="-999")

            output_dia1 = os.path.join(output_path, name_dia1)
            pdf_dia1.to_csv(output_dia1, sep=',', na_rep="-999")
         
            output_dia_mean1 = os.path.join(output_path, name_dia_mean1)
            pdf_dia_mean1.to_csv(output_dia_mean1, sep=',', na_rep="-999")
            output_bio1 = os.path.join(output_path, name_bio1)
            pdf_bio1.to_csv(output_bio1, sep=',', na_rep="-999")
            output_bio_mean1 = os.path.join(output_path, name_bio_mean1)
            pdf_bio_mean1.to_csv(output_bio_mean1, sep=',', na_rep="-999")

            output_delta_dia1 = os.path.join(output_path, name_delta_dia1)
            pdf_delta_dia1.to_csv(output_delta_dia1, sep=',', na_rep="-999")
            output_delta_dia_mean1 = os.path.join(output_path, name_delta_dia_mean1)
            pdf_delta_dia_mean1.to_csv(output_delta_dia_mean1, sep=',', na_rep="-999")
            output_delta_bio1 = os.path.join(output_path, name_delta_bio1)
            pdf_delta_bio1.to_csv(output_delta_bio1, sep=',', na_rep="-999")
            output_delta_bio_mean1 = os.path.join(output_path, name_delta_bio_mean1)
            pdf_delta_bio_mean1.to_csv(output_delta_bio_mean1, sep=',', na_rep="-999")
        
            output_dia2 = os.path.join(output_path, name_dia2)
            pdf_dia2.to_csv(output_dia2, sep=',', na_rep="-999")
            output_dia_mean2 = os.path.join(output_path, name_dia_mean2)
            pdf_dia_mean2.to_csv(output_dia_mean2, sep=',', na_rep="-999")
            output_bio2 = os.path.join(output_path, name_bio2)
            pdf_bio2.to_csv(output_bio2, sep=',', na_rep="-999")
            output_bio_mean2 = os.path.join(output_path, name_bio_mean2)
            pdf_bio_mean2.to_csv(output_bio_mean2, sep=',', na_rep="-999")
            output_delta_dia2 = os.path.join(output_path, name_delta_dia2)
            pdf_delta_dia2.to_csv(output_delta_dia2, sep=',', na_rep="-999")
            output_delta_dia_mean2 = os.path.join(output_path, name_delta_dia_mean2)
            pdf_delta_dia_mean2.to_csv(output_delta_dia_mean2, sep=',', na_rep="-999")
            output_delta_bio2 = os.path.join(output_path, name_delta_bio2)
            pdf_delta_bio2.to_csv(output_delta_bio2, sep=',', na_rep="-999")
            output_delta_bio_mean2 = os.path.join(output_path, name_delta_bio_mean2) 
            pdf_delta_bio_mean2.to_csv(output_delta_bio_mean2, sep=',', na_rep="-999")

            
            #remove the first row of the delta_bio
            pdf_delta_bio_mean22 = pdf_delta_bio_mean2[1:]
            #pdf_delta_bio_mean2["d_bio_mean"] .plot(label=mm)
            #pdf_delta_bio_mean2.to_csv(name_delta_bio_mean2, sep=',', na_rep="-999")
            #set up plot
            pyplot.plot(pdf_delta_bio_mean22['Year'],pdf_delta_bio_mean22['d_bio_mean'],label = mm)
#======================================================================================
#end for the rest file processing
#======================================================================================
            #pdf_age1.to_csv(name_age1, sep=',', na_rep="-999")
            #pdf_age_mean1.to_csv(name_age_mean1, sep=',', na_rep="-999")

            #name_tr = mm + "_tr.csv"  # "output_tr.csv"
            #name_tr_mean = mm + "_tr_mean.csv"  # "output_tr_mean.csv"

            #pdf_input1.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
            #pdf_mean1.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
            print('bingo')



#        pdf_input = pd.merge(pdf_input, pdf_input1, how='outer')  # merge the input dataframes
#        pdf_input.sort_values("year", inplace=True)  # sort values according to years

    #years_index = pdf_input["year"]                          #get the "year" column for the final dataframe
    #pdf_input.index = years_index                            #put it as the final index
    #pdf_input = pdf_input.drop(pdf_input.columns[0],axis=1)              #delect the first column of years
    #correct the index Yizhao 2019/7/10
#    index = list(range(0, len(pdf_input["year"])))
#    pdf_input.index = index
#    index_length = len(pdf_input["year"])
#    pdf_input2 = pdf_input.copy()
#    pdf_input2 = pdf_input2.drop(pdf_input.columns[0], axis=1)  # delect the first column of years
    #copy the values to another dataframe


    #remove the years column for BAI calculation Yizhao 2019/7/10
    #pdf_input2 = pdf_input.drop(columns=["year"])
    #BAI calculation Yizhao 2019/7/10
#    bai_sum = pdf_input.copy()
#    bai_sum[bai_sum.columns[1:len(bai_sum.columns)]] = np.nan

    #do calculation in each column
#    for key, value in pdf_input2.iteritems():
#        col_current = value
#        # set initial values
#        bai = np.zeros(index_length + 1)  # basal area increment
#        tr_accum = np.zeros(index_length + 1)  # tree ring accumulation
#        for i in range(len(col_current)):
#            #print(col_current[i])
#            if pd.isna(col_current[i]):
#                col_current[i] = 0
#                bai[i + 1] = bai[i]
#                tr_accum[i + 1] = tr_accum[i]
#            else:
#                tr_accum[i + 1] = tr_accum[i] + col_current[i]
#                bai[i + 1] = 3.1415926 * (tr_accum[i + 1] * tr_accum[i + 1] - tr_accum[i] * tr_accum[i])
#                bai[i + 1] = bai[i + 1] / 100      #translate into cm2
#        bai_sum[key] = bai[1:(index_length + 1)]

        # put the row names(years) back
#    years = range(int(t_start), int(t_end) + 1)
#    pdf_input2.index = years
#    bai_sum.index = years

    # statistical summary
   # pdf_mean = pdf_input2.mean(axis=1)
   # pdf_max = pdf_input2.max(axis=1)
   # pdf_min = pdf_input2.min(axis=1)
   # pdf_std = pdf_input2.std(axis=1)
   # pdf_c_summary = pdf_input2.describe()
    #pdf_upper = pdf_mean + pdf_std
    #pdf_lower = pdf_mean - pdf_std

   # bai_mean = bai_sum.mean(axis=1)
   # bai_max = bai_sum.max(axis=1)
   # bai_min = bai_sum.min(axis=1)
   # bai_std = bai_sum.std(axis=1)
   # bai_summary = bai_sum.describe()


    # need to put a transposition here to get the index summary
    # pdf_r_summary
    # print(pdf_mean)
    # ===================================================================================
    # plotting configuration
    # ===================================================================================
    #noted for global synthesis Yizhao 2019/12/23
    #pyplot.plot(pdf_delta_bioo_mean1['Year'],pdf_delta_bioo_mean1['d_bio_mean'],label = mm)
    #pyplot.plot(pdf_delta_bio_mean22['Year'],pdf_delta_bio_mean22['d_bio_mean'],label = mm)
    pyplot.legend(loc='upper left')
    pyplot.ylabel('AABI (kgC $tree^{-1} year^{-1}$)')
    pyplot.xlabel('year')
    pyplot.show()

    # pyplot.figure()
    # bai_mean.plot(label = 'BAI mean')
    # pyplot.legend(loc = 'upper left')
    # pyplot.ylabel('BAI (cm2)')
    # pyplot.xlabel('year')

    #change name pattern for global synthesis Yizhao 2019/12/22
    # n_lat = str(lat_in)
    # n_lon = str(lon_in)
    #name_tr = mm+"_tr.csv" #"output_tr.csv"
    #name_tr_mean = mm+"_tr_mean.csv"#"output_tr_mean.csv"
    # output the plot file
    #pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
    # bai_sum.to_csv(path_or_buf="output_bai_sum.csv", sep=',', na_rep="-999")
    # pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
    # bai_mean.to_csv(path_or_buf="output_bai_mean.csv", sep=',', na_rep="-999")
'''