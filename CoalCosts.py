import pandas as pd
import os

# Change user_name and path accordingly
user_name = 'mr_smith'
path = f'/Users/{user_name}/Desktop/'


def getPlantList():
    """ subsets and cleans EIA-923 page 1 data for use in equity optimization model """

    # Import Comprehensive Power Plant List From EIA-923 Page 1
    cpl = pd.read_csv("EIA923GenFuel2020.csv")

    # Subset coal plants by AER code
    cpl = cpl[
        ['Plant Id', 'Combined Heat And\nPower Plant', 'Plant Name', 'Plant State', 'EIA Sector Number',
         'AER\nFuel Type Code', 'Total Fuel Consumption\nMMBtu', 'Net Generation\n(Megawatthours)']]
    cpl.rename(
        columns={'Plant Id': 'ORIS_ID', 'Combined Heat And\nPower Plant': 'Combined_Heat', 'Plant Name': 'Plant_Name',
                 'Plant State': 'State', 'EIA Sector Number': 'EIA_Sector', 'AER\nFuel Type Code': 'AER',
                 'Total Fuel Consumption\nMMBtu': 'FuelCon_MMBTU',
                 'Net Generation\n(Megawatthours)': 'Gen_MWh'}, inplace=True)
    cpl = cpl[cpl['AER'].str.contains('COL|WOC')]

    # Filter out any potential non-operational plants
    cpl = cpl[cpl.FuelCon_MMBTU != 0]
    cpl = cpl[cpl.Gen_MWh > 0]

    # Filter out co-gen plants, and EIA sectors that are not of interest
    cpl = cpl[cpl['ORIS_ID'] != 99999]
    cpl = cpl[(cpl.EIA_Sector != 3) & (cpl.EIA_Sector != 7)]
    cpl = cpl[cpl['Combined_Heat'] == 'N']

    # Sum individual generator consumption, and generation for plant totals
    cpl.loc[:, 'NetGen_MWh'] = cpl.groupby(['ORIS_ID'])['Gen_MWh'].transform('sum')
    cpl.loc[:, 'NetFuelCon_MMBTU'] = cpl.groupby(['ORIS_ID'])['FuelCon_MMBTU'].transform('sum')

    # Clean up
    cpl = cpl.drop_duplicates(subset=['ORIS_ID', 'Plant_Name'])
    cpl = cpl.reset_index(drop=True)
    del cpl['FuelCon_MMBTU']
    del cpl['Gen_MWh']

    # Local file output
    cpl_output = os.path.join(path, 'CoalPlantList.csv')
    cpl.to_csv(cpl_output, index=False)

    return cpl


def getRegCoalCosts():
    """ calculates annual operation costs for regulated coal plants """

    # Load coal plant list for merge
    cpl = getPlantList()

    # Load fuel cost data for coal plants from EIA-923 page 5
    fcl = pd.read_csv("EIA923FuelCosts2020.csv")

    fcl = fcl[
        ['YEAR', 'MONTH', 'Plant Id', 'Plant Name', 'FUEL_GROUP', 'Regulated', 'Average Heat\nContent', 'FUEL_COST']]

    fcl.rename(columns={'Plant Id': 'ORIS_ID', 'Average Heat\nContent': 'Avg_Heat_Content'}, inplace=True)

    # Print average coal plant heat content, and filter out unregulated coal plants
    fcl = fcl[fcl['FUEL_GROUP'] == 'Coal']
    print("Average heat content for all coal plants (2020): ", fcl['Avg_Heat_Content'].mean())

    fcl_reg = fcl[fcl['Regulated'] == 'REG']

    # Clean
    del fcl_reg['Avg_Heat_Content']
    fcl_reg = fcl_reg.astype({"FUEL_COST": float})

    fcl_reg = fcl_reg.groupby('ORIS_ID')["FUEL_COST"].mean().rename("Avg_Fuel_Cost").reset_index()
    fcl_reg['Avg_Fuel_Cost'] = fcl_reg['Avg_Fuel_Cost'] / 100  # for units of $/MMBTU

    # Merge dataframes based on ORIS ID
    coalCostsReg = pd.merge(cpl, fcl_reg, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsReg['Heat_Rate'] = coalCostsReg['NetFuelCon_MMBTU'] / coalCostsReg['NetGen_MWh']
    coalCostsReg['Marginal_Fuel_Cost'] = (coalCostsReg['Heat_Rate'] * coalCostsReg['Avg_Fuel_Cost'])

    # Parameter values taken from Lazard and NREL ATB 2020
    coalCostsReg['VOM'] = 4.5  # $/MWh
    coalCostsReg['Coal_VOPEX'] = coalCostsReg['Marginal_Fuel_Cost'] + coalCostsReg['VOM']  # $/MWh
    coalCostsReg['Coal_FOPEX'] = 40  # $/kW-yr

    # Local file output
    ccr_output = os.path.join(path, 'CoalCostsReg.csv')
    coalCostsReg.to_csv(ccr_output, index=False)

    return coalCostsReg


# Unregulated Coal Plants
def getUnrCoalCosts():
    """ estimates annual operation costs for unregulated coal plants """

    # Load coal plant list for merge
    cpl = getPlantList()

    # Load fuel cost data for coal plants from EIA-923 page 5
    fcl = pd.read_csv("EIA923FuelCosts2020.csv")

    fcl = fcl[
        ['YEAR', 'MONTH', 'Plant Id', 'Plant Name', 'FUEL_GROUP', 'Regulated', 'Average Heat\nContent', 'FUEL_COST']]
    fcl.rename(columns={'Plant Id': 'ORIS_ID', 'Average Heat\nContent': 'Avg_Heat_Content'}, inplace=True)

    # Filter out regulated coal plants
    fcl_unr = fcl[fcl['Regulated'] == 'UNR']

    # Check average heat content of unregulated coal plants specifically
    print("Average heat content of UNR coal plants: ", fcl_unr['Avg_Heat_Content'].mean())

    # Clean
    del fcl_unr['FUEL_COST']

    fcl_unr['Fuel_Cost'] = 1.925  # Calculated outside of code
    fcl_unr.groupby('ORIS_ID')["FuelCost"].mean().rename("Avg_Fuel_Cost").reset_index()

    # Merge dataframes based on ORIS ID
    coalCostsUnr = pd.merge(cpl, fcl_unr, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsUnr['Heat_Rate'] = coalCostsUnr['NetFuelCon_MMBTU'] / coalCostsUnr['NetGen_MWh']
    coalCostsUnr['Marginal_Fuel_Cost'] = (coalCostsUnr['Heat_Rate'] * coalCostsUnr['Avg_Fuel_Cost'])

    # Parameter values taken from Lazard and NREL ATB 2020
    coalCostsUnr['VOM'] = 4.5  # $/MWh
    coalCostsUnr['Coal_VOPEX'] = coalCostsUnr['Marginal_Fuel_Cost'] + coalCostsUnr['VOM']  # $/MWh
    coalCostsUnr['Coal_FOPEX'] = 40  # $/kW-yr

    # Local file output
    ccu_output = os.path.join(path, 'CoalCostsUnr.csv')
    coalCostsUnr.to_csv(ccu_output, index=False)

    return coalCostsUnr


def mergeCosts():
    """ merges annual operation cost dataframes for regulated and unregulated coal plants (2020) """

    costsReg = getRegCoalCosts()
    costsUnr = getUnrCoalCosts()

    costsTotal = pd.concat([costsReg, costsUnr], ignore_index=True)

    # Local file output
    cct_output = os.path.join(path, 'CoalCostsTotal.csv')
    costsTotal.to_csv(cct_output, index=False)

    return costsTotal
