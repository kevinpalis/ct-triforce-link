#!/usr/bin/env python3
'''
	TBD

    Run the script with -h flag for command-line usage help (ie. python3 mapping.py -h).
    @author Kevin Palis <kevin.palis@gmail.com>
'''
import pandas as pd
from fuzzywuzzy import fuzz
from datetime import datetime, date

import sys
import getopt
import traceback

#just a test
s = pd.Series([1, 3, 5, 7, 6, 8])
print (s)

entso = pd.read_csv('../data/entso.csv')
platts = pd.read_csv('../data/platts.csv')
gppd = pd.read_csv('../data/gppd.csv')

print(entso.head())
print(f"\nEntso RowCount: {len(entso.index)}")
print(platts.head())
print(f"\nPlatts RowCount: {len(platts.index)}")
print(gppd.head())
print(f"\nGPPD RowCount: {len(gppd.index)}")