#!/usr/bin/env python3
'''
	Unit tests for TriforceLink

    Run using this command at the main triforce directory: python3 -m pytest -v
    Note that these are very simple tests just to show how I would go about developing such a module.
    If given more time, and if this is a module that will eventually process prod data, I would add more tests
    that will also check the number of entso-gppd-platts mapping based off of a known good result. Lastly, I would add more fixture data.
    But for the purpose of this coding exercise, I think the following tests are sufficient.

    @author Kevin Palis <kevin.palis@gmail.com>
'''
from triforce import mapping
from triforce.util.tl_utility import ReturnCodes
import pytest

#Test running the mapper with no parameters, ie. everything set as default
def test_map_data_main_all_defaults():
    assert mapping.main([]) == ReturnCodes.SUCCESS

#Test running the mapper with an invalid ENTSO file
def test_map_data_invalid_entso_file():
    assert mapping.main(['-e', 'invalid_entso_test.csv']) == ReturnCodes.ERROR_PARSING_FILE

#Test running the mapper with an invalid GPPD file
def test_map_data_invalid_gppd_file():
    assert mapping.main(['-g', 'invalid_gppd_test.csv']) == ReturnCodes.ERROR_PARSING_FILE

#Test running the mapper with an invalid Platts file
def test_map_data_invalid_platts_file():
    assert mapping.main(['-p', 'invalid_platts_test.csv']) == ReturnCodes.ERROR_PARSING_FILE

#Test running the mapper with higher verbosity
def test_map_data_main_all_defaults_verbose():
    assert mapping.main(['-v']) == ReturnCodes.SUCCESS

#Test running the mapper with plant_names normalization turned on
def test_map_data_with_normalize_names():
    assert mapping.main(['-n', 'True']) == ReturnCodes.SUCCESS
