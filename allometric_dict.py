#The function is to get the allometric relationships
#for each site
import csv
import math
import os

def allometric_dict(mm,dbh):
    #global biomass
    #mf = os.getcwd() + "\\rwl_metadata_2020_4_18_all_nontrw_non_species_removed_to_shp.csv"
    mf = os.path.join(os.path.dirname(__file__), "rwl_metadata_ITRDB.csv")
    #mf = "C:\\rwl_metadata_2020_4_18_all_nontrw_non_species_removed_to_shp.csv"
    #mf = "/home/ning/qianniu/TR_NEW/rwl_metadata_2020_4_18_all_nontrw_non_species_removed_to_shp.csv"
    #print(os.getcwd())
    #file_list = []  # create an empty list
    # lat_s = 2500
    # lat_e = 4900
    # lon_s = -13000
    # lon_e = -7000

    #print(mm)
    with open(mf) as f:
        reader = csv.DictReader(f)

        for row in reader:
            #start = row['start']
            #end = row['end']
            name = row['name']
            region = row['region']
            species = row['species']
            lat = row['lat']
            lon = row['lon']

            #print("name=",name)
            #print("mm=",mm)
            if mm == name:
                #print("yes")
                #print(mm)
                #print("yes")
                nn = species
                #print(nn)
#Europe
                # if (nn == "ABAL"):
                #     biomass = math.exp(-2.3958 + 2.4494 * math.log(dbh))
                #
                # elif (nn == "BEPE"):
                #     biomass = math.exp(-2.0013 + 2.3683 * math.log(dbh))
                #
                # elif (nn == "BEPU"):
                #     biomass = math.exp(-1.9147 + 2.2081 * math.log(dbh))
                #
                # elif (nn == "CASA"):
                #     biomass = math.exp(-1.8351 + 2.2916 * math.log(dbh))
                #
                # elif (nn == "CDLI"):
                #     biomass = 37.21449 + (-8.08322 * dbh) + (0.644812 * (dbh ** 2))
                #
                # elif (nn == "FASY"):
                #     biomass = math.exp(-1.6594 + 2.3589 * math.log(dbh))
                #
                # elif (nn == "LADE"):
                #     biomass = math.exp(-1.6512 + 2.2312 * math.log(dbh))
                #
                # elif (nn == "PCAB"):
                #     biomass = math.exp(-1.8865 + 2.3034 * math.log(dbh))
                #
                # elif (nn == "PIBR"):
                #     biomass = math.exp(4.874 + 2.239 * math.log(dbh))
                #
                # elif (nn == "PICE"):
                #     biomass = math.exp(-3.0675 + 2.5298 * math.log(dbh))
                #
                # elif (nn == "PINI"):
                #     biomass = math.exp(-2.0236 + 2.3345 * math.log(dbh))
                #
                # elif (nn == "PIPI"):
                #     biomass = math.exp(-2.5918 + 2.422 * math.log(dbh))
                #
                # elif (nn == "PIPN"):
                #     biomass = math.exp(-3.351 + 2.71 * math.log(dbh))
                #
                # elif (nn == "PISY"):
                #     biomass = math.exp(-2.1575 + 2.3097 * math.log(dbh))
                #
                # elif (nn == "PONI"):
                #     biomass = math.exp(-2.0236 + 2.3345 * math.log(dbh))
                #
                # elif (nn == "PIUN"):
                #     biomass = math.exp(-2.764 + 2.076 * math.log(dbh))
                #
                # elif (nn == "PPTM"):
                #     biomass = 0.0519 * (dbh ** 2.545)
                #
                # elif (nn == "PSME"):
                #     biomass = math.exp(-2.3298 + 2.4818 * math.log(dbh))
                #
                # elif (nn == "QUPE"):
                #     biomass = math.exp(-2.3364 + 2.5068 * math.log(dbh))
                #
                # elif (nn == "QURO"):
                #     biomass = math.exp(-2.684 + 2.7274 * math.log(dbh))
                #
                # elif (nn == "RO"):
                #     biomass = math.exp(-1.8468 + 2.2656 * math.log(dbh))
                #
                # elif (nn == "TICO"):
                #     biomass = math.exp(-7.402 + 2.62245 * math.log(dbh))
                #
                # elif (nn == 'QUSP'):
                #     biomass = math.exp(-2.0705 + 2.4410 * math.log(dbh))
                # else:
                #     biomass = -999

            #print("no")
            #else:
            #    biomass = -999
#Asia


#USA
                if (nn == 'ABAM' or nn == 'ABBA' or nn == 'ABCO'
                or nn == 'ABMA'):
                    biomass = math.exp(-3.1774 + 2.6426 * math.log(dbh))

                elif (nn == 'ABLA'):
                    biomass = math.exp(-2.3123  + 2.3482 * math.log(dbh))

                elif (nn == 'ACRU' or nn == 'BELE'):
                    biomass = math.exp(-1.9123 + 2.3651 * math.log(dbh))

                elif (nn == 'ACSH'):
                    biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

                elif (nn == 'CADE'):
                    biomass = math.exp(-11.8235 + 2.7334 * math.log(dbh))

                elif (nn == 'CYGL' or nn == 'CYOV'):
                    biomass = math.exp(-1.326 + 2.761 * math.log(dbh))

                elif (nn == 'CHNO'or nn == 'JUOC'):
                    biomass = math.exp(-2.6327 + 2.4757 * math.log(dbh))

                elif (nn == 'FAGR'):
                    biomass = 0.084 * math.pow(dbh,2.572)

                elif (nn == 'JUOS' or nn == 'JUSC'):
                    biomass = math.exp(-0.7152 + 1.7029 * math.log(dbh))

                elif (nn == 'JUVI'):
                    biomass = math.exp(-2.0336 + 2.2592 * math.log(dbh))

                elif (nn == 'LALY' or nn == 'LAOC'):
                    biomass = math.exp(-2.3012 + 2.3853 * math.log(dbh))

                elif (nn == 'LITU'):
                    biomass = math.exp(-2.48 + 2.4835 * math.log(dbh))

                elif (nn == 'PCEN'):
                    biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))

                elif (nn == 'PCGL'):
                    #print(dbh)
                    biomass = math.exp(-2.1364 + 2.3233 * math.log(dbh))
                    #print(biomass)

                elif (nn == 'PCMA'):
                    biomass = math.exp(-1.7823 + 2.1777 * math.log(dbh))

                elif (nn == 'PCPU'):
                    biomass = math.exp(-2.1364 + 2.3233 * math.log(dbh))

                elif (nn == 'PCRU'):
                    biomass = math.exp(-2.0773 + 2.3323 * math.log(dbh))

                elif (nn == 'PCSI'):
                    biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))

                elif (nn == 'PIAR' or nn == 'PIBA' or nn == 'PICO' or nn == 'PIEC'
                or nn == 'PIJE' or nn == 'PILO' or nn == 'PIMR' or nn == 'PIPA'
                or nn == 'PIPU'):
                    biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))

                elif (nn == 'PIED' or nn == 'PIRE' or nn == 'PIRI' or nn == 'PITA'):
                    biomass = math.exp(-2.5356 + 2.4349 * math.log(dbh))

                elif (nn == 'PIFL' or nn == 'PILA' or nn == 'PIPO' or nn == 'PIAL'
                or nn == 'PISF'):
                    biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

                elif (nn == 'PIST'):
                    biomass = math.exp(5.2831 + 2.0369 * math.log(dbh))

                elif (nn == 'PIVI'):
                    biomass = math.exp(-2.5918 + 2.422 * math.log(dbh))

                elif (nn == 'PPDE' or nn == 'PPGR'):
                    biomass = math.exp(-2.2094 + 2.3867 * math.log(dbh))

                elif (nn == 'PPTR'):
                    biomass = math.exp(4.4564 + 2.4486 * math.log(dbh))

                elif (nn == 'PSMA'):
                    biomass = math.exp(-2.4623 + 2.4852 * math.log(dbh))

                elif (nn == 'PSME'):
                    biomass = math.exp(-2.3298 + 2.4818 * math.log(dbh))

                elif (nn == 'QUAL' or nn == 'QUCO'):
                    biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

                elif (nn == 'QUDG'):
                    biomass = 0.0683*math.pow(dbh,2.5697)

                elif (nn == 'QUFA' or nn == 'QULO' or nn == 'QULY'):
                    biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

                elif (nn == 'QUMA' or nn == 'QUMU' or nn == 'QUPA'):
                    biomass = 0.1447* math.pow(dbh,2.282)

                elif (nn == 'QURU' or nn == 'QUSH' or nn == 'QUST' or 'QUVE'):
                    biomass = math.exp(-2.0127 + 2.4342 * math.log(dbh))

                elif (nn == 'TADI' or nn =='THPL' or nn == 'TSCR' or nn == 'TSHE' or
                nn == 'TSME' or nn == 'LIDE'):
                    biomass = math.exp(-2.7096 + 2.1942 * math.log(dbh))

                elif (nn == 'THOC'):
                    biomass = math.exp(-2.0336 + 2.2592 * math.log(dbh))

                elif (nn == 'TSCA'):
                    biomass = math.exp(-2.2304 + 2.4435 * math.log(dbh))

                elif (nn == 'CADN'):
                    biomass = math.exp(-2.0705 + 2.441 * math.log(dbh))

                elif (nn == 'CHLA'):
                    biomass = math.exp(-2.6327 + 2.4757 * math.log(dbh))

                elif (nn == 'MIXD'):
                    biomass = math.exp(-2.5497 + 2.5011 * math.log(dbh))

                elif (nn == 'PINE'):
                    biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

                elif (nn == 'PISP'):
                    biomass = math.exp(-3.2007 + 2.5339 * math.log(dbh))

                elif (nn == 'PITO'):
                    biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))

                elif (nn == 'PLRA'):
                    biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))

                elif (nn == 'QUCF' or nn == 'QUSP'):
                    biomass = math.exp(-2.0705 + 2.4410 * math.log(dbh))

                elif (nn == 'SAPC'):
                    biomass = math.exp(-2.6863 + 2.4561 * math.log(dbh))
                else:
                    biomass = -999
#canada
#TO CORRECT ABLA ONLY
                # if (nn == 'ABLA'):
                #    biomass = math.exp(-2.3123  + 2.3482 * math.log(dbh))
                # else:
                #    biomass = -999
#END FOR CORRECTION

                # if (nn == 'ABAM'):
                #     biomass = 0.0627 * math.pow(dbh,2.4921)
                #
                # elif (nn == 'ABBA'):
                #     biomass = 0.1764 * math.pow(dbh,2.1555)
                #
                #
                # elif (nn == 'CHNO'):
                #     biomass = 0.2498 * math.pow(dbh,2.1118)
                #
                # elif (nn == 'LALA'):
                #     biomass = 0.0946 * math.pow(dbh,2.3572)
                #
                # elif (nn == 'LALY'):
                #     biomass = math.exp(-2.3012 + 2.3853 * math.log(dbh))
                #
                # elif (nn == 'PCEN'):
                #     biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))
                #
                # elif (nn == 'PCGL'):
                #     biomass = 0.1077 * math.pow(dbh,2.3308)
                #
                # elif (nn == 'PCMA'):
                #     biomass = 0.1444 * math.pow(dbh, 2.2604)
                #
                # elif (nn == 'PCSI'):
                #     biomass = math.exp(-3.03 + 2.5567 * math.log(dbh))
                #
                # elif (nn == 'PIAL'):
                #     biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))
                #
                # elif (nn == 'PIBA'):
                #     biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))
                #
                # elif (nn == 'PIBN'):
                #     biomass = 0.2186 * math.pow(dbh, 1.94)
                #
                # elif (nn == 'PICO'):
                #     biomass = math.exp(-3.0506 + 2.6465 * math.log(dbh))
                #
                # elif (nn == 'PIFL'):
                #     biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))
                #
                # elif (nn == 'PINE'):
                #     biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))
                #
                # elif (nn == 'PIPO'):
                #     biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))
                #
                # elif (nn == 'PIRE'):
                #     biomass = 0.0847 * math.pow(dbh, 2.3503)
                #
                # elif (nn == 'PIST'):
                #     biomass = 0.1617 * math.pow(dbh, 2.142)
                #
                # elif (nn == 'PSME'):
                #     biomass = math.exp(-2.3298 + 2.4818 * math.log(dbh))
                #
                # elif (nn == 'QUMA'):
                #     biomass = 0.1447 * math.pow(dbh, 2.282)
                #
                # elif (nn == 'THOC'):
                #     biomass = 0.1148 * math.pow(dbh, 2.1439)
                #
                # elif (nn == 'THPL'):
                #     biomass = 0.1022 * math.pow(dbh, 2.088) + 0.0171 * math.pow(dbh, 1.999) + \
                #               0.0494 * math.pow(dbh, 1.922) + 0.0277 * math.pow(dbh, 2.139)
                #
                # elif (nn == 'TSME'):
                #     biomass = 0.5038 * math.pow(dbh, 2.0154)
                # else:
                #     biomass = -999

#mexico
                # if (nn == 'ABCO'):
                #     biomass = math.exp(-10.8036 + 2.7727 * math.log(dbh))
                #
                # elif (nn == 'PIAZ'):
                #     biomass = 0.0819 * math.pow(dbh, 2.4293)
                #
                # elif (nn == 'PICM'):
                #     biomass = math.exp(0.9173 + 1.073 * math.log(dbh))
                #
                # elif (nn == 'PIHR'):
                #     biomass = 0.0348 * math.pow(dbh, 2.5893)
                #
                # elif (nn == 'PIJE'):
                #     biomass = math.exp(-11.9976 + 2.952 * math.log(dbh))
                #
                # elif (nn == 'PILA'):
                #     biomass = math.exp(-10.5864 + 2.6863 * math.log(dbh))
                #
                # elif (nn == 'PIMZ'):
                #     biomass = 0.013 * math.pow(dbh, 3.046)
                #
                # elif (nn == 'PIPO'):
                #     biomass = math.exp(-2.6177 + 2.4638 * math.log(dbh))
                #
                # elif (nn == 'PSME'):
                #     biomass = 0.1354 * math.pow(dbh, .23033)
                #
                # elif (nn == 'TAMU'):
                #     biomass = math.exp(-2.6327 + 2.4757 * math.log(dbh))
                # else:
                #     biomass = -999
            #else:
            #    biomass = -999
            # if file_list:
            #print(biomass)
    return biomass
