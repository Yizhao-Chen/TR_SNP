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
        return start, end
    else:
        val = int(value)
        return val, val

def is_valid_int(value):
    try:
        int(value)
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
    with open(mf) as f:
        reader = csv.DictReader(f)
       # if len(lat_s) == 4:
       #     lat_st = '0' + lat_s
       # else:
       #     lat_st = lat_s

       # if len(lat_e) == 4:
       #     lat_et = '0' + lat_e
       # else:
       #     lat_et = lat_e

       # if len(lon_s) == 4:
       #     lon_st = '0' + lon_s
       # else:
       #     lon_st = lon_s

       # if len(lon_e) == 4:
       #     lon_et = '0' + lon_e
       # else:
       #     lon_et = lon_e

        for row in reader:
            start = row['start']
            end = row['end']
            id = row['id']
            region = row['region']
            species = row['species']
            lat = row['lat']
            lon = row['lon']

            if not is_valid_int(lat) or not is_valid_int(lon):
                continue  # 跳过无效的 lat 或 lon

            lat = int(lat)
            lon = int(lon)

            # if spec_in == 'all' and reg_in == 'all':
            #     if start <= year_in and end >= year_out and lat == lat_in and lon == lon_in:
            #         file_list.append(id)

            # elif spec_in != 'all' and reg_in == 'all':
            #     if start <= year_in and end >= year_out and species == spec_in: 
            #         file_list.append(id)
            # elif spec_in == 'all' and reg_in != 'all':
            #     if start <= year_in and end >= year_out and region == reg_in:
            #         file_list.append(id)
            # else:
            #     if start <= year_in and end >= year_out and species == spec_in and region == reg_in:
            #         file_list.append(id)


            # if spec_in == 'all' and reg_in == 'all':
            #     if (year_in == "" or start <= year_in) and (year_out == "" or end >= year_out) and \
            #     (lat_in == "" or lat == lat_in) and (lon_in == "" or lon == lon_in):
            #         file_list.append(id)

            if spec_in == 'all' and reg_in == 'all':
                if (year_in == "" or start <= year_in) and (year_out == "" or end >= year_out) and \
                (lat_start is None or (lat_start <= lat <= lat_end)) and \
                (lon_start is None or (lon_start <= lon <= lon_end)):
                    file_list.append(id)

            elif spec_in != 'all' and reg_in == 'all':
                if (year_in == "" or start <= year_in) and (year_out == "" or end >= year_out) and \
                species == spec_in:
                    file_list.append(id)

            elif spec_in == 'all' and reg_in != 'all':
                if (year_in == "" or start <= year_in) and (year_out == "" or end >= year_out) and \
                region == reg_in:
                    file_list.append(id)

            else:
                if (year_in == "" or start <= year_in) and (year_out == "" or end >= year_out) and \
                species == spec_in and region == reg_in:
                    file_list.append(id)

    return file_list
            #else:
            #    messagebox.showerror("ERROR","No data fits")
            #    os._exit()

