import pandas as pd
import numpy as np
import os
from netCDF4 import Dataset
from datetime import datetime

def getWindSpeedClass():
    """ constructs dataframe of wind speed classes based on ranges of average wind speeds """

    # create array of wind speed classes
    class_list = list(range(1, 11))

    # create array of minimum wind speeds correlating to wind speed class
    min_speed = [9.01, 8.77, 8.57, 8.35, 8.07, 7.62, 7.1, 6.53, 5.9, 1.72]  # units of m/s

    # create array of wind CAPEX values corresponding to wind speed class (values for 2021, adapted from NREL ATB)
    wind_capex = [1642.02, 1523.73, 1492.62, 1483.59, 1522.56, 1665.03, 1830.93, 2168.57, 2548.91, 2690.06]

    wind_dict = {'Wind_Speed_Class': class_list, 'Minimum_Speed': min_speed, 'Wind_CAPEX': wind_capex}

    wind_class = pd.DataFrame(wind_dict)

    return wind_class

def getWindCAPEX(lat, long):
    """ calculate land-based wind capital expenditure (CAPEX) based on geographic location (average wind speed) """

def getWindCosts ():
    """ calculate the total annual cost (capital expenditure + operation) of a wind farm """

    # initialize parameters from NREL ATB 2020, and Lazard v14.0
    wind_FOM = 40  # $/kW-yr

def getSolarCosts ():
    """ calculate the total annual cost (capital expenditure + operations) of a utility-scale solar PV farm   """

    # initialize parameters from NREL ATB 2020, and Lazard v14.0
    solar_FOM = 15  # $/kW-yr
    solar_CAPEX = 1300  # $/kW
