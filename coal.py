import pandas as pd
import argparse
import os

local_path = os.path.dirname(os.path.abspath(__file__))
coal_output = os.path.join(local_path, 'coal_data_output/')

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--year', type=int, choices=[2015, 2016, 2017, 2018, 2019, 2020], required=True,
                    help='Data year. Must be in 2015-2020 (inclusive).')
args = parser.parse_args()


def getPlantList():
    """ Function to return relevant EIA-923 page 1 coal plant data for use in decarb + equity optimization model """

    year = args.year
    # Import Comprehensive Power Plant List From EIA-923 Page 1
    file_path = os.path.join(local_path, f'coal_plant_data/EIA923GenFuel{year}.csv')
    cpl = pd.read_csv(file_path)

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
    cpl_output = os.path.join(coal_output, 'CoalPlantList.csv')
    cpl.to_csv(cpl_output, index=False)

    return cpl


def getRegCoalCosts():
    """ calculates annual operation costs (FOPEX, VOPEX) for regulated coal plants """

    year = args.year
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
    print("Average heat content for all coal plants (2020): ", fcl['Avg_Heat_Content'].mean())

    fcl = fcl[fcl['Regulated'] == 'REG']

    # Clean
    del fcl['Avg_Heat_Content']
    fcl = fcl.astype({'FUEL_COST': float})

    fcl_reg = fcl.groupby('ORIS_ID')["FUEL_COST"].mean().rename("Avg_Fuel_Cost").reset_index()
    fcl_reg['Avg_Fuel_Cost'] = fcl_reg['Avg_Fuel_Cost'] / 100  # for units of $/MMBTU

    # Merge dataframes based on ORIS ID
    coalCostsReg = pd.merge(cpl, fcl_reg, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsReg.loc[:, 'Heat_Rate'] = coalCostsReg['NetFuelCon_MMBTU'] / coalCostsReg['NetGen_MWh']
    coalCostsReg.loc[:, 'Marginal_Fuel_Cost'] = (coalCostsReg['Heat_Rate'] * coalCostsReg['Avg_Fuel_Cost'])

    # Parameter values taken from Lazard and NREL ATB 2020
    coalCostsReg.loc[:, 'VOM'] = 4.5  # $/MWh
    coalCostsReg.loc[:, 'Coal_VOPEX'] = coalCostsReg['Marginal_Fuel_Cost'] + coalCostsReg['VOM']  # $/MWh
    coalCostsReg.loc[:, 'Coal_FOPEX'] = 40 * (10**3)  # $/MW-yr

    # Local file output
    reg_output = os.path.join(coal_output, 'CoalCostsReg.csv')
    coalCostsReg.to_csv(reg_output, index=False)

    return coalCostsReg


# Unregulated Coal Plants
def getUnrCoalCosts():
    """ estimates annual operation costs for unregulated coal plants """

    year = args.year
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
    print("Average heat content of UNR coal plants: ", fcl['Avg_Heat_Content'].mean())

    fcl.loc[:, 'Fuel_Cost'] = 1.925  # $/MMBTU --> calculated outside of code

    fcl = fcl.astype({'Fuel_Cost': float})
    fcl_unr = fcl.groupby('ORIS_ID')['Fuel_Cost'].mean().rename('Avg_Fuel_Cost').reset_index()

    # Merge dataframes based on ORIS ID
    coalCostsUnr = pd.merge(cpl, fcl_unr, on=['ORIS_ID'])

    # Calculate annualized marginal cost of fuel
    coalCostsUnr.loc[:, 'Heat_Rate'] = coalCostsUnr['NetFuelCon_MMBTU'] / coalCostsUnr['NetGen_MWh']
    coalCostsUnr.loc[:, 'Marginal_Fuel_Cost'] = (coalCostsUnr['Heat_Rate'] * coalCostsUnr['Avg_Fuel_Cost'])

    # Parameter values taken from Lazard and NREL ATB 2020
    coalCostsUnr.loc[:, 'VOM'] = 4.5  # $/MWh
    coalCostsUnr.loc[:, 'Coal_VOPEX'] = coalCostsUnr['Marginal_Fuel_Cost'] + coalCostsUnr['VOM']  # $/MWh
    coalCostsUnr.loc[:, 'Coal_FOPEX'] = 40 * (10**3)  # $/MW-yr

    # Local file output
    unr_output = os.path.join(coal_output, 'CoalCostsUnr.csv')
    coalCostsUnr.to_csv(unr_output, index=False)

    return coalCostsUnr


def mergeCosts():
    """ merges annual operation cost dataframes for regulated and unregulated coal plants  """

    year = args.year
    
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
    print(f'Files in {cwd!r}: {files}')

    print(mergeCosts())
    print('Finished!')


if __name__ == '__main__':
    main()
