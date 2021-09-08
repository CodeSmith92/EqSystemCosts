import pandas as pd
import argparse
import geopandas as gpd
from shapely.geometry import Point
import os

local_path = os.path.dirname(os.path.abspath(__file__))

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--data_year', type=int, choices=[2016, 2017, 2018, 2019, 2020],
                    help='Year of data extraction. Must '
                         'be in 2016-2020 (inclusive).',
                    required=True)
parser.add_argument('--api_key', type=str, help='NREL API Key. Sign up @ https://developer.nrel.gov/signup/',
                    required=True)
parser.add_argument('--email', type=str, help='Email address.', required=True)
parser.add_argument('--geometry', type=str, help='Option for choosing sites.', choices=['grid', 'state'], required=True)
parser.add_argument('--min_lat', type=float, help='Required if geometry=grid')
parser.add_argument('--max_lat', type=float, help='Required if geometry=grid')
parser.add_argument('--min_lon', type=float, help='Required if geometry=grid')
parser.add_argument('--max_lon', type=float, help='Required if geometry=grid')
parser.add_argument('--states', nargs='+', type=str,
                    help="Required if geometry=state, e.g. 'PA OH NY'.. Input == 'CONTINENTAL' for entire US.")
parser.add_argument('--deg_resolution', type=float, default=.04, help='Approximate resolution of coordinate grid. '
                                                                      'Used for geometry=state or geometry=grid,'
                                                                      'default .04')

args = parser.parse_args()


def getCoords():  # Source code from ijbd (GitHub user)
    if args.geometry == 'grid':
        coordinates = []

        lat = args.min_lat
        while lat <= args.max_lat:
            lon = args.min_lon
            while lon <= args.max_lon:
                coordinates.append((lat, lon))
                lon += args.deg_resolution
            lat += args.deg_resolution
        return coordinates

    states = args.states
    if 'CONTINENTAL' in args.states:
        states = ['AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'ID', 'IL',
                  'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO',
                  'MT', 'NE', 'NV', 'NH', 'NH', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR',
                  'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
                  'WY']

    # get outer bounds
    usShp = gpd.read_file(os.path.join(local_path, 'states/s_11au16.shp'))
    statesShp = usShp[usShp['STATE'].isin(states)]

    coordinates = []

    bounds = statesShp.total_bounds

    min_lon = round(bounds[0], 2)
    min_lat = round(bounds[1], 2)
    max_lon = round(bounds[2], 2)
    max_lat = round(bounds[3], 2)

    lat = min_lat

    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            if statesShp.contains(Point(lon, lat)).any():
                coordinates.append((lat, lon))
            lon += args.deg_resolution
        lat += args.deg_resolution

    return coordinates


def getSolarData(year, lat, lon):  # Source code from ijbd (GitHub user)

    solarCSV = os.path.join(local_path, f'solar_data_output/{lat}_{lon}_nsrdb.csv')

    if not os.path.exists(solarCSV):
        nsrdb_url = 'https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-download.csv'

        params = {'api_key': args.api_key,
                  'email': args.email,
                  'wkt': f'POINT({lon}+{lat})',
                  'names': year,
                  'utc': 'true'
                  }

        params_str = '&'.join([f'{key}={params[key]}' for key in params])
        download_url = f'{nsrdb_url}?{params_str}'
        print(download_url)

        # Save resource CSV files
        solarResource = pd.read_csv(download_url)
        solarResource.to_csv(solarCSV, index=False)

    solarResourceDescription = pd.read_csv(solarCSV)
    solarResourceDescription = solarResourceDescription.head(1)
    # Check actual NSRDB lat/lon
    nsrdbLat = solarResourceDescription.at[0, 'Latitude']
    nsrdbLon = solarResourceDescription.at[0, 'Longitude']
    elevation = solarResourceDescription.at[0, 'Elevation']

    return lat, lon, nsrdbLat, nsrdbLon, elevation


def getSolarCosts():
    """Load NREL ATB data for access to future cost projections (2021-2035)"""

    atb_path = os.path.join(local_path, 'ATB/ATB2021.csv')
    atb = pd.read_csv(atb_path)

    sol_atb = atb[['TECH', 'YEAR', 'CAPEX_($/MW)', 'FOPEX_($/MW)']]

    sol_atb = sol_atb[sol_atb['TECH'] == 'Solar']
    del sol_atb['TECH']

    convert_dict = {'YEAR': int,
                    'CAPEX_($/MW)': float,
                    'FOPEX_($/MW)': float
                    }

    sol_atb = sol_atb.astype(convert_dict).reset_index(drop=True)

    print(sol_atb)
    print(sol_atb.dtypes)

    return sol_atb


def mergeData():
    year = args.data_year
    timespan = range(2021, 2031)

    sol_atb = getSolarCosts()

    print(getCoords())
    coords = getCoords()
    print(f'{len(coords)} coordinates found...')

    data = []
    for i in range(len(coords)):
        lat = coords[i][0]
        lon = coords[i][1]

        data.append(getSolarData(year, lat, lon))

    solarCosts = pd.DataFrame(data, columns=('lat', 'lon', 'nsrdbLat', 'nsrdbLon', 'elevation'))

    for y in timespan:
        if y == 2021:
            solarCosts.loc[:, 'CAPEX_($/MW)_2021'] = sol_atb.iloc[0]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2021'] = sol_atb.iloc[0]['FOPEX_($/MW)']

        elif y == 2022:
            solarCosts.loc[:, 'CAPEX_($/MW)_2022'] = sol_atb.iloc[1]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2022'] = sol_atb.iloc[1]['FOPEX_($/MW)']

        elif y == 2023:
            solarCosts.loc[:, 'CAPEX_($/MW)_2023'] = sol_atb.iloc[2]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2023'] = sol_atb.iloc[2]['FOPEX_($/MW)']

        elif y == 2024:
            solarCosts.loc[:, 'CAPEX_($/MW)_2024'] = sol_atb.iloc[3]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2024'] = sol_atb.iloc[3]['FOPEX_($/MW)']

        elif y == 2025:
            solarCosts.loc[:, 'CAPEX_($/MW)_2025'] = sol_atb.iloc[4]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2025'] = sol_atb.iloc[4]['FOPEX_($/MW)']

        elif y == 2026:
            solarCosts.loc[:, 'CAPEX_($/MW)_2026'] = sol_atb.iloc[5]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2026'] = sol_atb.iloc[5]['FOPEX_($/MW)']

        elif y == 2027:
            solarCosts.loc[:, 'CAPEX_($/MW)_2027'] = sol_atb.iloc[6]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2027'] = sol_atb.iloc[6]['FOPEX_($/MW)']

        elif y == 2028:
            solarCosts.loc[:, 'CAPEX_($/MW)_2028'] = sol_atb.iloc[7]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2028'] = sol_atb.iloc[7]['FOPEX_($/MW)']

        elif y == 2029:
            solarCosts.loc[:, 'CAPEX_($/MW)_2029'] = sol_atb.iloc[8]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2029'] = sol_atb.iloc[8]['FOPEX_($/MW)']

        else:
            solarCosts.loc[:, 'CAPEX_($/MW)_2030'] = sol_atb.iloc[9]['CAPEX_($/MW)']
            solarCosts.loc[:, 'FOPEX_($/MW)_2030'] = sol_atb.iloc[9]['FOPEX_($/MW)']

    return solarCosts


def main():
    print(f'local path: {local_path}')  # quick check

    solarCosts = mergeData()

    out_path = os.path.join(local_path, 'solar_data_output/solar_costs.csv')

    solarCosts.to_csv(out_path, index=False)

    print('Fin')


if __name__ == '__main__':
    main()
