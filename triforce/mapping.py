#!/usr/bin/env python3
'''
	This is the main module for Triforce-link. This creates a mapping.csv file which maps power plants from 3 different data sources:
    1. ENTSO
    2. Platts
    3. GPPD
    These data come in the form of CSV files and by default located in data/ directory with the names entso.csv, platts.csv, and gppd.csv.
    However, this module provides you with the option to pass an arbitrary file using certain CLI parameters (all of which are optional).

    The mapping algorithm goes as follows:
    0. (Optional) Pre-process / Normalize Power Plant Names - uses the plant_names of ENTSO as the reference to do fuzzy matching to both Platts and GPPD.
        For all matches that pass a certain WRatio score (90), it replaces the plant_names in Platts and GPPD with the reference name from ENTSO, effectively "normalizing"
        the names for later queries/mapping. This increases the processing time quite a bit and so I opted to disable this by default, but simply setting a
        parameter (-n True) to the command call will enable this. The given test data benefits with only 2 additional mapping found because of this but other datasets
        may be able to benefit more.
    1. Phase 1 - Map ENTSO-GPPD-Platts using plant name, country, and fuel type. 
        - Depending on whether step 0 ran (normalized power plant names), the plant_name matching will either employ fuzzy matching (effectively) or just a basic substring match
    2. Phase 2 - Create temporary dataframes/tables based on platts_plant_id mapping of GPPD and Platts, then use that to replace nulls in Phase 1 (ie. power plants it wasn't able to map).

    Lastly, this module uses the following libraries/technologies:
    * Pandas = for all data processing
    * Padasql = for SQL access to dataframes/tables
    * Fuzzywuzzy = for fuzzy matching (ex. using WRatio scorer)
    * Pytest = for unit testing
    > the docker container this script comes in with should already provision all necessary installations

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
    #print(argv)
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
            is_verbose = True

    try:
        entso = pd.read_csv(e_file)
        platts = pd.read_csv(p_file)
        gppd = pd.read_csv(g_file)
    except Exception as e:
        print(e)
        return ReturnCodes.ERROR_PARSING_FILE
    #A quick overview of row counts if ran verbose
    if is_verbose:
        #print(entso.head())
        print(f"Datafiles Loaded. Counts: \nEntso Rows = {len(entso.index)}")
        #print(platts.head())
        print(f"Platts Rows = {len(platts.index)}")
        #print(gppd.head())
        print(f"GPPD Rows = {len(gppd.index)}\n")

    #Attempt to cleanup/normalize plant_names for both platts and gppd using the plant_names from entso as primary reference, if normalize_plant_names is set to True.
    #This uses fuzzy matching with a score cutoff of 90. By default, extract functions use the scorer WRatio (ie. Weighted Ratio)
    #  which I think is best used in this case as I'm not very familiar with all the caveats fo matching power plant names across these 3 data sources.
    #  WRatio gives us a good scorer for the widest range of fuzzy matches.

    if normalize_plant_names == True:
        #get a list of reference plant_name from entso
        entso_plant_names = entso['plant_name'].tolist()
        #print(entso_plant_names)
        #Normalize Platts plant names
        print("Normalizing platts plant names...")
        #for each reference plant_name
        for plant_name in entso_plant_names:
            # find matches that pass the score requirement
            matches = process.extractBests(plant_name, platts['plant_name'], score_cutoff=90)
            #for each match, replace the platss.plant_name with the reference plant_name from entso
            for match in matches:
                platts.loc[platts['plant_name'] == match[0], 'plant_name'] = plant_name
        #do the same for GPPD
        print("Normalizing gppd plant names...")
        for plant_name in entso_plant_names:
            # find matches that pass the score requirement
            matches = process.extractBests(plant_name, gppd['plant_name'], score_cutoff=90)
            #for each match, replace the gppd.plant_name with the reference plant_name from entso
            for match in matches:
                gppd.loc[gppd['plant_name'] == match[0], 'plant_name'] = plant_name


    #Create a table/dataframe with matching platts_plant_id from platts and gppd
    #We use this to further map plants in entso that our first round of queries cannot map.
    #This is a secondary mapping strategy because the instruction mentioned that while platts_plant_id should map, it is sometimes incorrect or missing.
    q1 = "select p.*, g.gppd_plant_id from platts p \
        inner join gppd g on p.platts_plant_id=g.platts_plant_id"
    matched_platts_plant_id = sqldf(q1, locals())

    print("Starting Phase 1 mapping...")
    #Phase 1: Map using the most reliable criteria
    
    #A. ENTSO-GPPD Mapping: For all rows in ENTSO, map if following conditions are met, plant_name is the same or similar to GPPD plant_name 
    # AND the country is the same or similar, AND the unit_fuel is the same. Note that if normalize_plant_names (-n) was set, the name comparison would effectively 
    # include fuzzy matching, otherwise it is just a less complicated substring match.
    q2 = "select e.*, g.gppd_plant_id from entso e left join gppd g on ((e.plant_name like '%' || g.plant_name || '%' or \
        g.plant_name like '%' || e.plant_name || '%') and (e.country like '%' || g.country_long || '%' or g.country_long like '%' || e.country || '%') \
            and e.unit_fuel=g.plant_primary_fuel)"
    entso_gppd = sqldf(q2, locals())

    #B. ENTSO-GPPD-Platts mapping: For all rows in ENTSO-GPPD, map if following conditions are met: plant_name is the same or similar to Platts plant_name AND the country is the same or similar AND the unit_fuel is the same.
    # Note that if normalize_plant_names was set, the name comparison would effectively include fuzzy matching, otherwise it is a less complicated substring match.
    q3 = "select eg.*, p.platts_unit_id from entso_gppd eg left join platts p on ((eg.plant_name like '%' || p.plant_name || '%' or \
        p.plant_name like '%' || eg.plant_name || '%') and (eg.country like '%' || p.country || '%' or p.country like '%' || eg.country || '%') \
            and eg.unit_fuel=p.unit_fuel)"
    entso_gppd_platts = sqldf(q3, locals())

    if is_verbose:
        print ("Removing duplicates in the mapped tables/dataframes...")
    #Remove duplicates in place, keeping only the first occurence (most of the duplicates are introduced by mapping to Platts, ie. 1 GPPD plant maps to multiple Platts units)
    entso_gppd_platts.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    #reset index as there are gaps after removing duplicate rows
    entso_gppd_platts=entso_gppd_platts.reset_index(drop=True)

    #Phase 2: Map using the joined table/dataframe matched_platts_plant_id. As mentioned, this is less reliable so we only use this to map the ones we weren't able to map in Phase 1
    #   This is also not as straightforward as Phase 1. For this phase we do the following:
    #   1. Create a table/dataframe with the output of phase 1 (entso_gppd_platts) left joined to the matched_platts_plant_id table (intersection table of platts and gppd where platts_plant_id matches)
    #       on platts_unit_id. This effectively gives us all gppd_plant_id from matched_platts_plant_id table.
    #   2. Create a table/dataframe with the output of phase 1 (entso_gppd_platts) left joined to the matched_platts_plant_id table (intersection table of platts and gppd where platts_plant_id matches)
    #       on gppd_plant_id. This effectively gives us all platts_unit_id from matched_platts_plant_id table.
    #   3. Use the two dataframes/tables to replace null values (plants we weren't able to map in phase 1) on columns gppd_plant_id and platts_unit_id respectively.
    print("Starting Phase 2 mapping...")
    q4 = "select egp.entso_unit_id, egp.unit_capacity, egp.unit_fuel, egp.country, egp.unit_name, egp.plant_name, egp.plant_capacity, mpp.gppd_plant_id, \
        egp.platts_unit_id from entso_gppd_platts egp left join matched_platts_plant_id mpp on egp.platts_unit_id=mpp.platts_unit_id"
    g1 = sqldf(q4, locals())

    #Remove duplicates in place, keeping only the first occurence (most of the duplicates are introduced by mapping to Platts, ie. 1 GPPD plant maps to multiple Platts units)
    g1.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    #reset index as there are gaps after removing duplicate rows
    g1=g1.reset_index(drop=True)
    if is_verbose:
        print("Filling nulls in column gppd_plant_id with mappings from phase 2...")
    entso_gppd_platts.fillna(g1,inplace=True)

    q5 = "select egp.entso_unit_id, egp.unit_capacity, egp.unit_fuel, egp.country, egp.unit_name, egp.plant_name, egp.plant_capacity, egp.gppd_plant_id, \
        mpp.platts_unit_id from entso_gppd_platts egp left join matched_platts_plant_id mpp on egp.gppd_plant_id=mpp.gppd_plant_id"
    g2 = sqldf(q5, locals())
    #remove duplicates
    g2.drop_duplicates(subset=['entso_unit_id'], inplace=True)
    #reset index as there are gaps after removing duplicate rows
    g2=g2.reset_index(drop=True)

    if is_verbose:
        print("Filling nulls in column platts_unit_id with mappings from phase 2...")
    entso_gppd_platts.fillna(g2,inplace=True)

    if is_verbose:
        print(f"Mapper was able to map all ENTSO plants except for {entso_gppd_platts.platts_unit_id.isnull().sum()} platts_unit_id and {entso_gppd_platts.gppd_plant_id.isnull().sum()} gppd_plant_id")

    #write output
    entso_gppd_platts.to_csv('mapping.csv', index=False, columns=['entso_unit_id', 'platts_unit_id', 'gppd_plant_id'])
    print("Mapping finished. Output is written as mapping.csv in the execution directory.")
    return ReturnCodes.SUCCESS

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