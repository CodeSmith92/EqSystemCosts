import pandas as pd
import argparse
import os

local_path = os.path.dirname(os.path.abspath(__file__))
coal_output = os.path.join(local_path, 'coal_data_output/')

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--data_year', type=int, choices=[2015, 2016, 2017, 2018, 2019, 2020], required=True,
                    help='Year for data extraction. Must be in 2015-2020 (inclusive).')
args = parser.parse_args()


def getPlantList():
    """ Function to return relevant EIA-923 page 1 coal plant data for use in decarb + equity optimization model """

    year = args.data_year
    # Import Comprehensive Power Plant List From EIA-923 Page 1
    file_path = os.path.join(local_path, f'coal_plant_data/EIA923GenFuel{year}.csv')
    cpl = pd.read_csv(file_path)

    # Subset coal plants by AER code
    cpl = cpl[
        ['Plant Id', 'Combined Heat And\nPower Plant', 'Plant Name', 'Plant State', 'EIA Sector Number',
         'AER\nFuel Type Code', 'Total Fuel Consumption\nMMBtu', 'Net Generation\n(Megawatthours)']]
    cpl.rename(
        columns={'Plant Id': 'ORIS_ID', 'Combined Heat And\nPower Plant': 'Combined_Heat', 'Plant Name': 'Plant_Name',
                 'Plant State': 'State', 'EIA Sector Number': 'EIA_Sector', 'AER\nFuel Type Code': 'Fuel_Type',
                 'Total Fuel Consumption\nMMBtu': 'FuelCon_MMBTU',
                 'Net Generation\n(Megawatthours)': 'Gen_MWh'}, inplace=True)

    cpl = cpl[cpl['Fuel_Type'].str.contains('COL|WOC')]

    # Filter out any potential non-operational plants
    cpl = cpl[cpl.FuelCon_MMBTU != 0]
    cpl = cpl[cpl.Gen_MWh > 0]

    # Filter out co-gen plants
    cpl = cpl[cpl['ORIS_ID'] != 99999]  # 999999 == state level fuel increment
    cpl = cpl[(cpl.EIA_Sector != 3) & (cpl.EIA_Sector != 7)]
    cpl = cpl[cpl['Combined_Heat'] == 'N']

    # Sum individual generator consumption, and and individual generator generation for plant totals
    cpl.loc[:, 'NetGen_MWh'] = cpl.groupby(['ORIS_ID'])['Gen_MWh'].transform('sum')
    cpl.loc[:, 'NetFuelCon_MMBTU'] = cpl.groupby(['ORIS_ID'])['FuelCon_MMBTU'].transform('sum')

    # Clean up
    cpl = cpl.drop_duplicates(subset=['ORIS_ID', 'Plant_Name'])
    cpl = cpl.reset_index(drop=True)

    del cpl['FuelCon_MMBTU']
    del cpl['Gen_MWh']

    # Save and output file
    cpl_output = os.path.join(coal_output, f'CoalPlantList{year}.csv')
    cpl.to_csv(cpl_output, index=False)

    return cpl


# Regulated Coal Plants
def getRegCoalCosts():
    """ Function to calculate annual variable operation costs (VOPEX) for regulated coal plants as reported by EIA-923.
    Values after 2020 are projections provided by NREL ATB 2021 """

    year = args.data_year

    # Load coal plant list for merge
    cpl = getPlantList()

    # Load fuel cost data for coal plants from EIA-923 page 5
    file_path = os.path.join(local_path, f'coal_plant_data/EIA923FuelCosts{year}.csv')
    fcl = pd.read_csv(file_path)

    fcl = fcl[
        ['YEAR', 'MONTH', 'Plant Id', 'Plant Name', 'FUEL_GROUP', 'Regulated', 'Average Heat\nContent', 'FUEL_COST']]

    fcl.rename(columns={'Plant Id': 'ORIS_ID', 'Average Heat\nContent': 'Avg_Heat_Content'}, inplace=True)

    # Print average coal plant heat content, and filter out unregulated coal plants
    fcl = fcl[fcl['FUEL_GROUP'] == 'Coal']
    print("Average heat content for all coal plants (2020): ", fcl['Avg_Heat_Content'].mean(), ' MMBTU/Short-ton')

    fcl = fcl[fcl['Regulated'] == 'REG']

    # Clean
    del fcl['Avg_Heat_Content']
    fcl = fcl.astype({'FUEL_COST': float})

    fcl_reg = fcl.groupby('ORIS_ID')["FUEL_COST"].mean().rename("Avg_Fuel_Cost_($/MMBTU)").reset_index()
    fcl_reg['Avg_Fuel_Cost_($/MMBTU)'] = fcl_reg['Avg_Fuel_Cost_($/MMBTU)'] / 100  # for units of $/MMBTU

    # Merge dataframes based on ORIS ID
    coalCostsReg = pd.merge(cpl, fcl_reg, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsReg.loc[:, 'Heat_Rate_(MMBTU/MWh)'] = coalCostsReg['NetFuelCon_MMBTU'] / coalCostsReg['NetGen_MWh']
    coalCostsReg.loc[:, 'Marginal_Fuel_Cost_($/MWh)'] = (coalCostsReg['Heat_Rate_(MMBTU/MWh)']
                                                         * coalCostsReg['Avg_Fuel_Cost_($/MMBTU)'])

    # Parameter values adapted from Lazard LCOE Analysis v14.0 and NREL ATB 2021
    coalCostsReg.loc[:, 'VOM_($/MWh)'] = 4.35
    coalCostsReg.loc[:, 'Coal_VOPEX_($/MWh)'] = coalCostsReg['Marginal_Fuel_Cost_($/MWh)'] + coalCostsReg['VOM_($/MWh)']
    coalCostsReg.loc[:, 'Coal_FOPEX_($/MW)'] = 31.75 * (10**3)  # $/MW-yr, assumed static in subsequent years

    # Local file output
    reg_output = os.path.join(coal_output, f'CoalCostsReg{year}.csv')
    coalCostsReg.to_csv(reg_output, index=False)

    return coalCostsReg


# Unregulated Coal Plants
def getUnrCoalCosts():
    """ Function to estimate annual variable operation costs for unregulated coal plants """

    year = args.data_year
    # Load coal plant list for merge
    cpl = getPlantList()

    # Load fuel cost data for coal plants from EIA-923 page 5
    file_path = os.path.join(local_path, f'coal_plant_data/EIA923FuelCosts{year}.csv')
    fcl = pd.read_csv(file_path)

    fcl = fcl[
        ['YEAR', 'MONTH', 'Plant Id', 'Plant Name', 'FUEL_GROUP', 'Regulated', 'Average Heat\nContent']]
    fcl.rename(columns={'Plant Id': 'ORIS_ID', 'Average Heat\nContent': 'Avg_Heat_Content'}, inplace=True)

    # Filter out regulated coal plants
    fcl = fcl[fcl['FUEL_GROUP'] == 'Coal']
    fcl = fcl[fcl['Regulated'] == 'UNR']

    # Check average heat content of unregulated coal plants specifically
    print("Average heat content of UNR coal plants: ", fcl['Avg_Heat_Content'].mean(), ' MMBTU/Short-ton')

    fcl.loc[:, 'Fuel_Cost'] = 1.925  # $/MMBTU --> see GitHub documentation

    # Actually an estimated fuel cost, but referred to as "Avg_Fuel_Cost" for dataframe merging
    fcl = fcl.astype({'Fuel_Cost': float})
    fcl_unr = fcl.groupby('ORIS_ID')['Fuel_Cost'].mean().rename('Avg_Fuel_Cost_($/MMBTU)').reset_index()

    # Merge dataframes based on ORIS ID
    coalCostsUnr = pd.merge(cpl, fcl_unr, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsUnr.loc[:, 'Heat_Rate_(MMBTU/MWh)'] = coalCostsUnr['NetFuelCon_MMBTU'] / coalCostsUnr['NetGen_MWh']
    coalCostsUnr.loc[:, 'Marginal_Fuel_Cost_($/MWh)'] = (coalCostsUnr['Heat_Rate_(MMBTU/MWh)']
                                                         * coalCostsUnr['Avg_Fuel_Cost_($/MMBTU)'])

    # Parameter values taken from Lazard and NREL ATB 2020
    coalCostsUnr.loc[:, 'VOM_($/MWh)'] = 4.35
    coalCostsUnr.loc[:, 'Coal_VOPEX_($/MWh)'] = coalCostsUnr['Marginal_Fuel_Cost_($/MWh)'] + coalCostsUnr['VOM_($/MWh)']
    coalCostsUnr.loc[:, 'Coal_FOPEX_($/MW)'] = 31.75 * (10**3)  # $/MW-yr

    # Local file output
    unr_output = os.path.join(coal_output, f'CoalCostsUnr{year}.csv')
    coalCostsUnr.to_csv(unr_output, index=False)

    return coalCostsUnr


def mergeCosts():
    """ merges annual operation cost dataframes for regulated and unregulated coal plants  """

    year = args.data_year

    costsReg = getRegCoalCosts()
    costsUnr = getUnrCoalCosts()

    costsTotal = pd.concat([costsReg, costsUnr], ignore_index=True)

    # Local file output
    cost_output = os.path.join(coal_output, f'coal_costs_total{year}.csv')
    costsTotal.to_csv(cost_output, index=False)

    return costsTotal


def main():
    print(local_path)

    cwd = os.getcwd()  # Get the current working directory (cwd)
    files = os.listdir(cwd)  # Get all the files in that directory
    print(f'Files in {cwd}: {files}')

    print(mergeCosts())
    print('Finito!')


if __name__ == '__main__':
    main()
