#age output only
#Yizhao 2020/6/2




import rpy2
import tzlocal
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
from allometric_dict import *

#add lat_in lon_in for global synthesis Yizh
def plot_age_only(fk):
    pyplot.rcParams['savefig.dpi'] = 300
    pyplot.rcParams['figure.dpi'] = 300

    TR_input_dir = fk[0]
    #print("hello")
    #print(fk[0])
    #get the file name without direct and file type Yizhao 2019/12/23
    mm = os.path.splitext(os.path.basename(fk[0]))[0]
    print("mm1" + mm)
    TR_input = r['read.tucson'](TR_input_dir)
    start = r['min'](r['as.numeric'](r['rownames'](TR_input)))
    end = r['max'](r['as.numeric'](r['rownames'](TR_input)))
    #r['as.numeric'](r['max'](r['rownames'](TR_input)))
    # get observation period
    TRW = r['data.frame'](year=r['seq'](start, end, 1))
    # select only important rows ( the tree (?) or series names, e.g. "LF317s")
    all = r['names'](TR_input)

    #The heteroscedastic variance structure was stabilized using adaptive power transformation prior to detrending.
    #The age/size-related trends in the raw data were removed from
    # all series using cubic smoothing spline detrending with a 50% frequency
    # from Babst et al 2019 DOI: 10.1126/sciadv.aat4313
    #TR_powt = dplR.powt(TR_input)
    #TR_de = dplR.detrend(TR_input, method="Spline")

    #biweight robust mean (an average that is unaffected by outliers)
    #TR_de1 = dplR.chron(TR_de)


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

        #create
        #pdf_dia = pdf_input.copy()      #diameter df
        #pdf_delta_dia = pdf_input.copy() #delta diameter df
        #pdf_bio = pdf_input.copy()      #biomass df
        #pdf_delta_bio = pdf_input.copy()  #delta biomass df
        pdf_age = pdf_input.copy()
        #calculate biomass increment for each tree
        #column loop
        for i in range (0,len(pdf_input.columns)):
            #one column
            pdf_sub = pdf_input.iloc[:,i]
            #diameter = pdf_sub.copy()
            #biomass = pdf_sub.copy()
            #delta_dia = pdf_sub.copy()
            #delta_bio = pdf_sub.copy()
            age = pdf_sub.copy()
            #get the first non-NAN value and the year

            y_start = pdf_sub.first_valid_index()
            y_end = pdf_sub.last_valid_index()
            length = y_end - y_start + 1
            #year loop
            for k in range (y_start,(y_end +1)):
                if k == y_start:
                    if pdf_sub[k] == 0:
                        pdf_sub[k] = 1e-8
                    age[k] = 1
                    #diameter[k] = (2 * pdf_sub[k])/10    # cm
                    # get biomass based allometric relationships
                    #biomass[k] = allometric_dict(mm, diameter[k])
                    #print(biomass[k])
                    #delta_dia[k] = diameter[k]
                    #delta_bio[k] = biomass[k]
                else:
                    if pdf_sub[k] == 0:
                        pdf_sub[k] = 1e-8
                    age[k] = age[k-1] + 1
                    #diameter[k] = diameter[k-1] + (2 * pdf_sub[k])/10    # cm
                    #if (k == 134):
                    #    print(pdf_sub[k])
                    #    print(diameter[k])
                    #print(diameter[k-1])
                    #get biomass based allometric relationships
                    #biomass[k] = allometric_dict(mm,diameter[k])
                    #print(biomass[k])
                    #delta_dia[k] = diameter[k] - diameter[k - 1]
                    #delta_bio[k] = biomass[k] - biomass[k-1]

                    #print(k)
                    #print(pdf_sub[k])
                    #print(i)

                count = k - pdf_sub.index[0]
                #pdf_dia.iloc[count,i] = diameter[k]
                #pdf_delta_dia.iloc[count,i] = delta_dia[k]
                #pdf_bio.iloc[count,i] = biomass[k]  # biomass df
                #pdf_delta_bio.iloc[count,i] = delta_bio[k]  # delta biomass df
                pdf_age.iloc[count,i] = age[k]

        #Get the mean values using biweight robust mean
        #convert to r df first
        #r_pdf_dia = rpy2.robjects.conversion.py2ri(pdf_dia)
        #r_pdf_delta_dia = rpy2.robjects.conversion.py2ri(pdf_delta_dia)
        #r_pdf_bio = rpy2.robjects.conversion.py2ri(pdf_bio)
        #r_pdf_delta_bio = rpy2.robjects.conversion.py2ri(pdf_delta_bio)
        r_pdf_age = rpy2.robjects.conversion.py2ri(pdf_age)

        #r_pdf_dia_mean = dplR.chron(r_pdf_dia)
        #r_pdf_delta_dia_mean = dplR.chron(r_pdf_delta_dia)
        #r_pdf_bio_mean = dplR.chron(r_pdf_bio)
        #r_pdf_delta_bio_mean = dplR.chron(r_pdf_delta_bio)
        r_pdf_age_mean = dplR.chron(r_pdf_age)

        #pdf_dia_mean = rpy2.robjects.conversion.ri2py(r_pdf_dia_mean)
        #pdf_delta_dia_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_dia_mean)
        #pdf_bio_mean = rpy2.robjects.conversion.ri2py(r_pdf_bio_mean)
        #pdf_delta_bio_mean = rpy2.robjects.conversion.ri2py(r_pdf_delta_bio_mean)
        pdf_age_mean = rpy2.robjects.conversion.ri2py(r_pdf_age_mean)

        #pdf_dia_mean.insert(0, "Year", years)
        #pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
        #pdf_dia_mean.columns = ['Year', 'dia_mean','samp.depth']

        #pdf_delta_dia_mean.insert(0, "Year", years)
        #pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
        #pdf_delta_dia_mean.columns = ['Year', 'd_dia_mean','samp.depth']

        #pdf_bio_mean.insert(0, "Year", years)
        #pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
        #pdf_bio_mean.columns = ['Year', 'bio_mean','samp.depth']

        #pdf_delta_bio_mean.insert(0, "Year", years)
        #pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
        #pdf_delta_bio_mean.columns = ['Year', 'd_bio_mean','samp.depth']

        pdf_age_mean.insert(0, "Year", years)
        pdf_age_mean.columns = ['Year','age','samp.depth']
        #simple mean values
        #pdf_dia_mean = pdf_dia.iloc[:,1:(len(pdf_dia.columns)+1)].mean(1)
        #pdf_delta_dia_mean = pdf_delta_dia.iloc[:,1:(len(pdf_delta_dia.columns)+1)].mean(1)
        #pdf_bio_mean = pdf_bio.iloc[:,1:(len(pdf_bio.columns)+1)].mean(1)
        #pdf_delta_bio_mean = pdf_delta_bio.iloc[:,1:(len(pdf_delta_bio.columns)+1)].mean(1)

        #name_dia = mm + "_dia.csv"
        #name_dia_mean = mm + "_dia_mean.csv"
        #name_bio = mm + "_bio.csv"
        #name_bio_mean = mm + "_bio_mean.csv"
        name_age = mm + "_age.csv"
        name_age_mean = mm + "_age_mean.csv"

        #name_delta_dia = mm + "_delta_dia.csv"
        #name_delta_dia_mean = mm + "_delta_dia_mean.csv"
        #name_delta_bio = mm + "_delta_bio.csv"
        #name_delta_bio_mean = mm + "_delta_bio_mean.csv"


        #pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
        #pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
        #pdf_dia.to_csv(name_dia, sep=',', na_rep="-999")
        #pdf_dia_mean.to_csv(name_dia_mean, sep=',', na_rep="-999")
        #pdf_bio.to_csv(name_bio, sep=',', na_rep="-999")
        #pdf_bio_mean.to_csv(name_bio_mean, sep=',', na_rep="-999")

        #pdf_delta_dia.to_csv(name_delta_dia, sep=',', na_rep="-999")
        #pdf_delta_dia_mean.to_csv(name_delta_dia_mean, sep=',', na_rep="-999")
        #pdf_delta_bio.to_csv(name_delta_bio, sep=',', na_rep="-999")
        #pdf_delta_bio_mean.to_csv(name_delta_bio_mean, sep=',', na_rep="-999")

        pdf_age.to_csv(name_age,sep=',',na_rep="-999")
        pdf_age_mean.to_csv(name_age_mean,sep=',',na_rep="-999")


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
            #pdf_dia1 = pdf_input1.copy()  # diameter df
            #pdf_delta_dia1 = pdf_input1.copy()  # delta diameter df
            #pdf_bio1 = pdf_input1.copy()  # biomass df
            #pdf_delta_bio1 = pdf_input1.copy()  # delta biomass df
            pdf_age1 = pdf_input1.copy()
            # calculate biomass increment for each tree
            # column loop
            for i in range(0, len(pdf_input1.columns)):
                # one column
                pdf_sub1 = pdf_input1.iloc[:, i]
                #diameter1 = pdf_sub1.copy()
                #biomass1 = pdf_sub1.copy()
                #delta_dia1 = pdf_sub1.copy()
                #delta_bio1 = pdf_sub1.copy()
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
                        age1[k] = 1
                        #diameter1[k] = (2 * pdf_sub1[k]) / 10  # cm
                        # get biomass based allometric relationships
                        #biomass1[k] = allometric_dict(mm, diameter1[k])
                        # print(biomass[k])
                        #delta_dia1[k] = diameter1[k]
                        #delta_bio1[k] = biomass1[k]
                    else:
                        if pdf_sub1[k] == 0:
                            pdf_sub1[k] = 1e-8
                        age1[k] = age1[k-1] + 1
                        #diameter1[k] = diameter1[k - 1] + (2 * pdf_sub1[k]) / 10  # cm
                        # get biomass based allometric relationships
                        #biomass1[k] = allometric_dict(mm, diameter1[k])
                        # print(biomass[k])
                        #delta_dia1[k] = diameter1[k] - diameter1[k - 1]
                        #delta_bio1[k] = biomass1[k] - biomass1[k - 1]


                    count1 = k - pdf_sub1.index[0]
                    #pdf_dia1.iloc[count1, i] = diameter1[k]
                    #pdf_delta_dia1.iloc[count1, i] = delta_dia1[k]
                    #pdf_bio1.iloc[count1, i] = biomass1[k]  # biomass df
                    #pdf_delta_bio1.iloc[count1, i] = delta_bio1[k]  # delta biomass df
                    pdf_age1.iloc[count1,i] = age1[k]
            # Get the mean values using biweight robust mean
            # convert to r df first
            #r_pdf_dia1 = rpy2.robjects.conversion.py2ri(pdf_dia1)
            #r_pdf_delta_dia1 = rpy2.robjects.conversion.py2ri(pdf_delta_dia1)
            #r_pdf_bio1 = rpy2.robjects.conversion.py2ri(pdf_bio1)
            #r_pdf_delta_bio1 = rpy2.robjects.conversion.py2ri(pdf_delta_bio1)
            r_pdf_age1 = rpy2.robjects.conversion.py2ri(pdf_age1)

            #r_pdf_dia_mean1 = dplR.chron(r_pdf_dia1)
            #r_pdf_delta_dia_mean1 = dplR.chron(r_pdf_delta_dia1)
            #r_pdf_bio_mean1 = dplR.chron(r_pdf_bio1)
            #r_pdf_delta_bio_mean1 = dplR.chron(r_pdf_delta_bio1)
            r_pdf_age_mean1 = dplR.chron(r_pdf_age1)

            #pdf_dia_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_dia_mean1)
            #pdf_delta_dia_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_delta_dia_mean1)
            #pdf_bio_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_bio_mean1)
            #pdf_delta_bio_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_delta_bio_mean1)
            pdf_age_mean1 = rpy2.robjects.conversion.ri2py(r_pdf_age_mean1)

            # Get the mean values
            #pdf_dia_mean1 = pdf_dia1.iloc[:, 1:(len(pdf_dia1.columns) + 1)].mean(1)
            #pdf_delta_dia_mean1 = pdf_delta_dia1.iloc[:, 1:(len(pdf_delta_dia1.columns) + 1)].mean(1)
            #pdf_bio_mean1 = pdf_bio1.iloc[:, 1:(len(pdf_bio1.columns) + 1)].mean(1)
            #pdf_delta_bio_mean1 = pdf_delta_bio1.iloc[:, 1:(len(pdf_delta_bio1.columns) + 1)].mean(1)

            #pdf_dia_mean1.insert(0, "Year", years)
            # pdf_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            #pdf_dia_mean1.columns = ['Year', 'dia_mean', 'samp.depth']

            #pdf_delta_dia_mean1.insert(0, "Year", years)
            # pdf_delta_dia_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            #pdf_delta_dia_mean1.columns = ['Year', 'd_dia_mean', 'samp.depth']

            #pdf_bio_mean1.insert(0, "Year", years)
            # pdf_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            #pdf_bio_mean1.columns = ['Year', 'bio_mean', 'samp.depth']

            #pdf_delta_bio_mean1.insert(0, "Year", years)
            # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            #pdf_delta_bio_mean1.columns = ['Year', 'd_bio_mean', 'samp.depth']

            pdf_age_mean1.insert(0, "Year", years)
            # pdf_delta_bio_mean = pdf_dia_mean.drop(pdf_dia_mean.columns[2],axis=1)
            pdf_age_mean1.columns = ['Year', 'age_mean', 'samp.depth']


            #name_dia1 = mm + "_dia.csv"
            #name_dia_mean1 = mm + "_dia_mean.csv"
            #name_bio1 = mm + "_bio.csv"
            #name_bio_mean1 = mm + "_bio_mean.csv"

            #name_delta_dia1 = mm + "_delta_dia.csv"
            #name_delta_dia_mean1 = mm + "_delta_dia_mean.csv"
            #name_delta_bio1 = mm + "_delta_bio.csv"
            #name_delta_bio_mean1 = mm + "_delta_bio_mean.csv"

            name_age1 = mm + "_age.csv"
            name_age_mean1 = mm + "_age_mean.csv"

            # pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
            # pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
            #pdf_dia1.to_csv(name_dia1, sep=',', na_rep="-999")
            #pdf_dia_mean1.to_csv(name_dia_mean1, sep=',', na_rep="-999")
            #pdf_bio1.to_csv(name_bio1, sep=',', na_rep="-999")
            #pdf_bio_mean1.to_csv(name_bio_mean1, sep=',', na_rep="-999")
            pdf_age1.to_csv(name_age1, sep=',', na_rep="-999")
            pdf_age_mean1.to_csv(name_age_mean1, sep=',', na_rep="-999")

            #pdf_delta_dia1.to_csv(name_delta_dia1, sep=',', na_rep="-999")
            #pdf_delta_dia_mean1.to_csv(name_delta_dia_mean1, sep=',', na_rep="-999")
            #pdf_delta_bio1.to_csv(name_delta_bio1, sep=',', na_rep="-999")
            #pdf_delta_bio_mean1.to_csv(name_delta_bio_mean1, sep=',', na_rep="-999")


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
    # plotting
    # very simple right now,need major revision to make it more useful
    # ===================================================================================
    #noted for global synthesis Yizhao 2019/12/23
    #pyplot.figure()
    #pdf_mean.plot(label='TR mean')
    #pdf_upper.plot(label='upper error')
    #pdf_lower.plot(label='lower error')
    #pyplot.legend(loc='upper left')
    #pyplot.ylabel('TRW (mm)')
    #pyplot.xlabel('year')

    #pyplot.figure()
    #bai_mean.plot(label = 'BAI mean')
    #pyplot.legend(loc = 'upper left')
    #pyplot.ylabel('BAI (cm2)')
    #pyplot.xlabel('year')
    #pyplot.show()

    #change name pattern for global synthesis Yizhao 2019/12/22
    #n_lat = str(lat_in)
    #n_lon = str(lon_in)
    #name_tr = mm+"_tr.csv" #"output_tr.csv"
    #name_tr_mean = mm+"_tr_mean.csv"#"output_tr_mean.csv"
    # output the plot file
    #pdf_input.to_csv(path_or_buf=name_tr, sep=',', na_rep="-999")
    #bai_sum.to_csv(path_or_buf="output_bai_sum.csv", sep=',', na_rep="-999")
    #pdf_mean.to_csv(path_or_buf=name_tr_mean, sep=',', na_rep="-999")
    #bai_mean.to_csv(path_or_buf="output_bai_mean.csv", sep=',', na_rep="-999")