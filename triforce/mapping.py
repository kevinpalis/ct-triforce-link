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

import sys
import getopt
import traceback

pysqldf = lambda q: sqldf(q, globals())

entso = pd.read_csv('../data/entso.csv')
platts = pd.read_csv('../data/platts.csv')
gppd = pd.read_csv('../data/gppd.csv')

#print(entso.head())
print(f"\nEntso RowCount: {len(entso.index)}")
#print(platts.head())
print(f"\nPlatts RowCount: {len(platts.index)}")
#print(gppd.head())
print(f"\nGPPD RowCount: {len(gppd.index)}")


#entsoMin = entso[["entso_unit_id", "plant_name", "country", "unit_fuel"]]
#print(type(entsoMin))

#check how many platts_plant_id actually match
q = "select p.platts_unit_id, p.plant_name as pName, g.plant_name as gName from platts p \
    inner join gppd g on p.platts_plant_id=g.platts_plant_id"
r = pysqldf(q)
print("Matching platts_plant_id:")
print(len(r.index))

# q1 = "select g.* from gppd g left join platts p on (g.platts_plant_id=p.platts_plant_id \
#     or (g.plant_name=p.plant_name and g.country_long=p.country and g.plant_primary_fuel=p.unit_fuel))"
# gppd_platts = pysqldf(q1)
# print("Matched platts and gppd:")
# print(len(gppd_platts.index))

q2 = "select e.*, g.gppd_plant_id, g.plant_name from entso e left join gppd g on ((e.plant_name like '%' || g.plant_name || '%' or \
     g.plant_name like '%' || e.plant_name || '%') and (e.country like '%' || g.country_long || '%' or g.country_long like '%' || e.country || '%') \
        and e.unit_fuel=g.plant_primary_fuel)"
entso_gppd = pysqldf(q2)
print("Matched platts and gppd:")
print(len(entso_gppd.index))
print(entso_gppd)

q3 = "select eg.*, p.platts_unit_id, p.unit_fuel, p.country from entso_gppd eg left join platts p on ((eg.plant_name like '%' || p.plant_name || '%' or \
     p.plant_name like '%' || eg.plant_name || '%') and (eg.country like '%' || p.country || '%' or p.country like '%' || eg.country || '%') \
        and eg.unit_fuel=p.unit_fuel)"
entso_gppd_platts = pysqldf(q3)
print("Matched entso_gppd_platts:")
print(len(entso_gppd_platts.index))
print(entso_gppd_platts)

entso_gppd_platts.drop_duplicates(subset=['entso_unit_id'], inplace=True)
print("Removed duplicates entso_gppd_platts:")
print(len(entso_gppd_platts.index))
print(entso_gppd_platts)
# for i in range(len(entso.index)):
#     p1 = entso["plant_name"].iloc[i]
#     print(p1)
#     print(process.extractBests(p1, platts['plant_name'], score_cutoff=90))
#     print('\n')

#platts
#print(entso["plant_name"].apply(lambda x: process.extractBests(x, platts["plant_name"].to_list(),score_cutoff=90)))
#gppd
#print(entso["plant_name"].apply(lambda x: process.extractBests(x, gppd["plant_name"].to_list(),score_cutoff=90)))

#test query
#q = "SELECT * FROM entso where unit_capacity < 400 LIMIT 10"
#r = pysqldf(q)
#print(r)