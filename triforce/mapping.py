#!/usr/bin/env python3
'''
	TBD

    Run the script with -h flag for command-line usage help (ie. python3 mapping.py -h).
    @author Kevin Palis <kevin.palis@gmail.com>
'''
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from datetime import datetime, date
from pandasql import sqldf
from util.tl_utility import *

import sys
import getopt
import traceback

def main(argv):
    #pysqldf = lambda q: sqldf(q, globals()) #-> unfortunately can't use this inside main, there is a bug with lambdas (https://github.com/yhat/pandasql/issues/53) and pandasql don't intend to work around it.
    #defaults
    is_verbose = False
    exit_code = ReturnCodes.SUCCESS
    e_file = '../data/entso.csv'
    p_file = '../data/platts.csv'
    g_file = '../data/gppd.csv'
    normalize_plant_names = False

    #Get and parse parameters
    try:
        opts, args = getopt.getopt(argv, "he:g:p:n:v", ["entsoFile=", "gppdFile=", "plattsFile=", "normalizePlantNames=", "verbose"])
        #print (opts, args)
    except getopt.GetoptError:
        # print ("OptError: %s" % (str(e1)))
        exitWithException(ReturnCodes.INVALID_OPTIONS)
    for opt, arg in opts:
        if opt == '-h':
            printUsageHelp(ReturnCodes.SUCCESS)
        elif opt in ("-e", "--entsoFile"):
            e_file = arg
        elif opt in ("-g", "--gppdFile"):
            g_file = arg
        elif opt in ("-p", "--plattsFile"):
            p_file = arg
        elif opt in ("-n", "--normalizePlantNames"):
            if arg == "True":
                normalize_plant_names = True
        elif opt in ("-v", "--verbose"):
            isVerbose = True

    entso = pd.read_csv(e_file)
    platts = pd.read_csv(p_file)
    gppd = pd.read_csv(g_file)
    
    #print(entso.head())
    print(f"\nEntso RowCount: {len(entso.index)}")
    #print(platts.head())
    print(f"\nPlatts RowCount: {len(platts.index)}")
    #print(gppd.head())
    print(f"\nGPPD RowCount: {len(gppd.index)}")


    #Attempt to cleanup plant_names for both platts and gppd using the plant_names from entso as primary reference
    #This uses fuzzy matching with a score cutoff of 90.
    #get a list of reference plant_name from entso
    entso_plant_names = entso['plant_name'].tolist()
    print(entso_plant_names)

    #for each reference plant_name
    if normalize_plant_names == True:
        print("Cleaning up platts plant names...")
        for plant_name in entso_plant_names:
            # find matches that pass the score requirement
            matches = process.extractBests(plant_name, platts['plant_name'], score_cutoff=90)
            #for each match, replace the platss.plant_name with the reference plant_name from entso
            for match in matches:
                platts.loc[platts['plant_name'] == match[0], 'plant_name'] = plant_name

        print("Cleaning up gppd plant names...")
        for plant_name in entso_plant_names:
            # find matches that pass the score requirement
            matches = process.extractBests(plant_name, gppd['plant_name'], score_cutoff=90)
            #for each match, replace the gppd.plant_name with the reference plant_name from entso
            for match in matches:
                gppd.loc[gppd['plant_name'] == match[0], 'plant_name'] = plant_name


    #entsoMin = entso[["entso_unit_id", "plant_name", "country", "unit_fuel"]]
    #print(type(entsoMin))

    #check how many platts_plant_id actually match
    q1 = "select p.*, g.gppd_plant_id from platts p \
        inner join gppd g on p.platts_plant_id=g.platts_plant_id"
    matched_platts_plant_id = sqldf(q1, locals())
    print("Matching platts_plant_id:")
    print(matched_platts_plant_id)
    print(len(matched_platts_plant_id.index))

    # q1 = "select g.* from gppd g left join platts p on (g.platts_plant_id=p.platts_plant_id \
    #     or (g.plant_name=p.plant_name and g.country_long=p.country and g.plant_primary_fuel=p.unit_fuel))"
    # gppd_platts = pysqldf(q1)
    # print("Matched platts and gppd:")
    # print(len(gppd_platts.index))

    #Phase 1: Match using the following criteria:
    #For all rows in ENTSO, match if following conditions are met: plant_name is the same or similar to (ie. a substring of) GPPD plant AND the country is the same or similar, 
    #and the unit_fuel is the same.
    q2 = "select e.*, g.gppd_plant_id from entso e left join gppd g on ((e.plant_name like '%' || g.plant_name || '%' or \
        g.plant_name like '%' || e.plant_name || '%') and (e.country like '%' || g.country_long || '%' or g.country_long like '%' || e.country || '%') \
            and e.unit_fuel=g.plant_primary_fuel)"
    entso_gppd = sqldf(q2, locals())
    print("Matched platts and gppd:")
    print(len(entso_gppd.index))
    print(entso_gppd)

    #For all rows in ENTSO, match if following conditions are met: plant_name is the same or similar to (ie. a substring of) Platts plant AND the country is the same or similar, 
    #and the unit_fuel is the same.
    q3 = "select eg.*, p.platts_unit_id from entso_gppd eg left join platts p on ((eg.plant_name like '%' || p.plant_name || '%' or \
        p.plant_name like '%' || eg.plant_name || '%') and (eg.country like '%' || p.country || '%' or p.country like '%' || eg.country || '%') \
            and eg.unit_fuel=p.unit_fuel)"
    entso_gppd_platts = sqldf(q3, locals())
    print("Matched entso_gppd_platts:")
    print(len(entso_gppd_platts.index))
    print(entso_gppd_platts)

    #Remove duplicates in place, keeping only the first occurence (most of the duplicates are introduced by mapping to Platts, ie. 1 GPPD plant maps to multiple Platts units)
    entso_gppd_platts.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    print("Removed duplicates entso_gppd_platts:")
    print(len(entso_gppd_platts.index))
    #print(entso_gppd_platts)
    #reset index as there are gaps after removing duplicate rows
    entso_gppd_platts=entso_gppd_platts.reset_index(drop=True)
    print("Index reset entso_gppd_platts:")
    print(entso_gppd_platts)
    #print(entso_gppd_platts[entso_gppd_platts['platts_unit_id'].isnull()])
    #print(entso_gppd_platts[entso_gppd_platts['gppd_plant_id'].isnull()])



    q4 = "select egp.entso_unit_id, egp.unit_capacity, egp.unit_fuel, egp.country, egp.unit_name, egp.plant_name, egp.plant_capacity, mpp.gppd_plant_id, \
        egp.platts_unit_id from entso_gppd_platts egp left join matched_platts_plant_id mpp on egp.platts_unit_id=mpp.platts_unit_id"
    g1 = sqldf(q4, locals())
    print("Joined to matched_platts_plant_id on platts_unit_id:")
    print(len(g1.index))
    print(g1)

    #Remove duplicates in place, keeping only the first occurence (most of the duplicates are introduced by mapping to Platts, ie. 1 GPPD plant maps to multiple Platts units)
    g1.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    print("Removed duplicates g1:")
    print(len(g1.index))
    #reset index as there are gaps after removing duplicate rows
    g1=g1.reset_index(drop=True)
    print(g1)

    print("Before Fill:")
    print(entso_gppd_platts)

    print("Filled nulls from values of g1:")
    entso_gppd_platts.fillna(g1,inplace=True)
    print(entso_gppd_platts)

    q5 = "select egp.entso_unit_id, egp.unit_capacity, egp.unit_fuel, egp.country, egp.unit_name, egp.plant_name, egp.plant_capacity, egp.gppd_plant_id, \
        mpp.platts_unit_id from entso_gppd_platts egp left join matched_platts_plant_id mpp on egp.gppd_plant_id=mpp.gppd_plant_id"
    g2 = sqldf(q5, locals())
    print("Joined to matched_platts_plant_id on gppd_plant_id:")
    print(len(g2.index))
    #print(g2)

    g2.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    print("Removed duplicates g2:")
    print(len(g2.index))
    #reset index as there are gaps after removing duplicate rows
    g2=g2.reset_index(drop=True)
    print(g2)

    print("Before Fill:")
    print(entso_gppd_platts.platts_unit_id.isnull().sum())

    print("Filled nulls from values of g1:")
    entso_gppd_platts.fillna(g2,inplace=True)
    print(entso_gppd_platts)
    print(f"Null counts: platts_unit_id={entso_gppd_platts.platts_unit_id.isnull().sum()} , gppd_plant_id={entso_gppd_platts.gppd_plant_id.isnull().sum()}")


    # for i in range(len(entso_gppd_platts.index)):
    #     if entso_gppd_platts.iloc[[i]].gppd_plant_id.isnull():
    #         entso_gppd_platts.iloc[[i]].gppd_plant_id='HAIII'
    #     print(entso_gppd_platts.iloc[i].gppd_plant_id)

    #entso_gppd_platts[entso_gppd_platts['gppd_plant_id'].isnull(), ['gppd_plant_id']] = gppd.loc[gppd['platts_plant_id'].isin(platts['platts_plant_id']),'gppd_plant_id']
    # entso_gppd_platts.loc[entso_gppd_platts.platts_unit_id.isnull(), 'platts_unit_id']='DAMNU!'
    # print("Replaced NULLS entso_gppd_platts:")
    # print(entso_gppd_platts)


    # for i in range(len(entso.index)):
    #     p1 = entso["plant_name"].iloc[i]
    #     print(p1)
    #     print(process.extractBests(p1, platts['plant_name'], score_cutoff=90))
    #     print('\n')


    #platts
    #print(entso_gppd_platts["plant_name"].apply(lambda x: process.extractBests(x, platts["plant_name"].to_list(),score_cutoff=90)))
    #gppd
    #print(entso["plant_name"].apply(lambda x: process.extractBests(x, gppd["plant_name"].to_list(),score_cutoff=90)))

    #test query
    #q = "SELECT * FROM entso where unit_capacity < 400 LIMIT 10"
    #r = pysqldf(q)
    #print(r)

#utility method for exception handling
def exitWithException(eCode):
    try:
        raise TLException(eCode)
    except TLException as e1:
        print("Error code: %s" % e1.code)
        TLUtility.printError(e1.message)
        #traceback.print_exc()
        sys.exit(eCode)

#prints usage help
def printUsageHelp(eCode):
    print (eCode)
    print ("python3 mapping.py -e <entsoFile:string> -g <gppdFile:string> -p <plattsFile:string> -n <normalizePlantNames:bool> -v")
    print ("\t-h = Usage help")
    print ("\t-e or --entsoFile = (OPTIONAL) Path to the CSV file with ENTSO data. Default (if unset): entso.csv in data directory")
    print ("\t-g or --gppdFile = (OPTIONAL) Path to the CSV file with GPPD data. Default (if unset): gppd.csv in data directory")
    print ("\t-p or --plattsFile = (OPTIONAL) Path to the CSV file with Platts data. Default (if unset): platts.csv in data directory")
    print ("\t-n or --normalizePlantNames = (OPTIONAL) Whether or not to perform names normalization based on plant_names in ENTSO file (this tend to increase runtime but more matches can be found). Default (if unset): True")
    print ("\t-v or --verbose = (OPTIONAL) Print the status of TL execution in more detail.")
    if eCode == ReturnCodes.SUCCESS:
        sys.exit(eCode)
    try:
        raise TLException(eCode)
    except TLException as e1:
        print (e1.message)
        traceback.print_exc()
        sys.exit(eCode)
        
if __name__ == "__main__":
	main(sys.argv[1:])