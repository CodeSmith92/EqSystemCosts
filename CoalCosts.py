import pandas as pd
import numpy as np
import os.path

# Import Comprehensive Power Plant List From EIA-923 Page 1
CoalPlantList = pd.read_csv("EIA923GenFuel2020.csv")

# Subset And Output Coal Plants Only By AER Code
CoalPlantList = CoalPlantList[
    ['Plant Id', 'Combined Heat And\nPower Plant', 'Plant Name', 'Plant State', 'EIA Sector Number',
     'AER\nFuel Type Code', 'Total Fuel Consumption\nMMBtu', 'Net Generation\n(Megawatthours)']]

CoalPlantList.rename(
    columns={'Plant Id': 'ORIS_ID', 'Combined Heat And\nPower Plant': 'Combined_Heat', 'Plant Name': 'Plant_Name',
             'Plant State': 'State', 'EIA Sector Number': 'SectorNumber', 'AER\nFuel Type Code': 'AER',
             'Total Fuel Consumption\nMMBtu': 'FuelCon_MMBTU',
             'Net Generation\n(Megawatthours)': 'Gen_MWh'}, inplace=True)

CoalPlantList = CoalPlantList[CoalPlantList['AER'].str.contains('COL|WOC')]

# Assuming No Fuel Consumption --> Plant Is Not Operational
CoalPlantList = CoalPlantList[CoalPlantList.FuelCon_MMBTU != 0]
CoalPlantList = CoalPlantList[CoalPlantList.Gen_MWh > 0]

# Filter Data
CoalPlantList = CoalPlantList[CoalPlantList['ORIS_ID'] != 99999]
CoalPlantList = CoalPlantList[(CoalPlantList.SectorNumber != 3) & (CoalPlantList.SectorNumber != 7)]
CoalPlantList = CoalPlantList[CoalPlantList['Combined_Heat'] == 'N']

# Sum Individual Generator Generation And Consumption Into New Columns
CoalPlantList.loc[:, 'NetGeneration_MWh'] = CoalPlantList.groupby(['ORIS_ID'])['Gen_MWh'].transform('sum')
CoalPlantList.loc[:, 'NetFuelCon_MMBTU'] = CoalPlantList.groupby(['ORIS_ID'])['FuelCon_MMBTU'].transform('sum')

# Define The Working Dataset, Drop Duplicates, And  Reset Index
CoalPlantList = CoalPlantList.drop_duplicates(subset=['ORIS_ID', 'Plant_Name'])
del CoalPlantList['FuelCon_MMBTU']
del CoalPlantList['Gen_MWh']
CPL_Clean = CoalPlantList.reset_index(drop=True)


# Load Fuel Cost Data for Coal Plants From EIA-923 Page 5
FuelCostList = pd.read_csv("EIA923FuelCosts2020.csv")

FuelCostList = FuelCostList[
    ['YEAR', 'MONTH', 'Plant Id', 'Plant Name', 'FUEL_GROUP', 'Regulated', 'Average Heat\nContent', 'FUEL_COST']]

FuelCostList.rename(columns={'Plant Id': 'ORIS_ID', 'Average Heat\nContent': 'AvgHeatContent'}, inplace=True)

# Check Average Heat Content
FuelCostList = FuelCostList[FuelCostList['FUEL_GROUP'] == 'Coal']
print("Average Heat Content (all coal plants): ", FuelCostList['AvgHeatContent'].mean())

# TOGGLE REG/UNR
FuelCostList = FuelCostList[FuelCostList['Regulated'] == 'REG']

# Regulated Coal Plants (skip to line 63 for UNR commands)
del FuelCostList['AvgHeatContent']
FuelCostList = FuelCostList.astype({"FUEL_COST": float})

FCL_Clean = FuelCostList.groupby('ORIS_ID')["FUEL_COST"].mean().rename("AVG_FUEL_COST").reset_index()
FCL_Clean['AVG_FUEL_COST'] = FCL_Clean['AVG_FUEL_COST']/100  # for units of $/MMBTU

# Unregulated Coal Plants
del FuelCostList['FUEL_COST']

# Check Average Heat Content of UNR Coal Plants
print("Average Heat Content: ", FuelCostList['AvgHeatContent'].mean())
FuelCostList['FuelCost']= 1.925  # Calculated Value
FCL_clean = FuelCostList.groupby('ORIS_ID')["FuelCost"].mean().rename("EST_FUEL_COST").reset_index()

# Merge Dataframes Based on ORIS ID
CoalCosts = pd.merge(CPL_Clean, FCL_Clean, on=['ORIS_ID'])

# Calculate Annualized Operation Costs
CoalCosts['HeatRate'] = CoalCosts['NetFuelCon_MMBTU']/CoalCosts['NetGeneration_MWh']  # RUN FOR REG
CoalCosts['MarginalFuelCost'] = (CoalCosts['HeatRate']*CoalCosts['AVG_FUEL_COST'])  # RUN FOR REG

CoalCosts['MarginalFuelCost'] = (CoalCosts['HeatRate']*CoalCosts['EST_FUEL_COST'])  # RUN FOR UNR

# Parameter Values from Lazard and NREL ATB 2020
CoalCosts['VOM'] = 4.4
CoalCosts['CoalVOPEX ($/MWh)'] = CoalCosts['MarginalFuelCost'] + CoalCosts['VOM']
CoalCosts['FOPEX ($/MW)'] = 4*10**3