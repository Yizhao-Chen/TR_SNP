#!/usr/bin/env python
"""
Test script to verify allodb can be imported through rpy2
"""
import rpy2
from rpy2.robjects import r
from rpy2.robjects.packages import importr
import pandas as pd
from rpy2.robjects import pandas2ri

# Activate pandas conversion
pandas2ri.activate()

try:
    # Import the allodb package
    print("Importing allodb...")
    allodb = importr('allodb')
    print("allodb package imported successfully!")
    
    # Execute an R command to get some data from allodb
    print("Loading test data from allodb...")
    r('data("biomass_family", package="allodb")')
    
    # Convert R dataframe to pandas
    biomass_family = r('biomass_family')
    
    # Convert to pandas dataframe
    print("Converting to pandas dataframe...")
    biomass_family_pd = pandas2ri.rpy2py_dataframe(biomass_family)
    
    # Display head of dataframe
    print("\nSample data from allodb:")
    print(biomass_family_pd.head())
    
    print("\nTest completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    exit(1) 