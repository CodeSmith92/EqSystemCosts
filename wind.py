import pandas as pd
import numpy as np
import argparse
import geopandas as gpd
from shapely.geometry import Point
import os

local_path = os.path.dirname(os.path.abspath(__file__))

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--data_year', type=int, choices=[2010, 2011, 2012, 2013, 2014], help='Year of data extraction. '
                                                                                          'Must be in 2010-2014 ('
                                                                                          'inclusive).', required=True)
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


def getWindData(year, lat, lon):  # Source code from ijbd (GitHub user)
    """ by year and coordinate --> retrieves wind resource data from NREL's WIND Toolkit, and cost data from ATB 2021
    """

    windCSV = os.path.join(local_path, f'wind_data_output/{lat}_{lon}_wtk.csv')

    if not os.path.exists(windCSV):
        wtk_url = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download'

        params = {'api_key': args.api_key,
                  'email': args.email,
                  'lat': lat,
                  'lon': lon,
                  'hubheight': 100,
                  'year': year,
                  'utc': 'true'
                  }

        params_str = '&'.join([f'{key}={params[key]}' for key in params])
        download_url = f'{wtk_url}?{params_str}'
        print(download_url)

        # Save resource CSV files
        windResource = pd.read_csv(download_url)
        windResource.to_csv(windCSV, index=False)

    # Find wind speed
    windSpeed100 = np.median(pd.read_csv(windCSV, skiprows=[0, 1, 3, 4], usecols=['Speed']).values)

    # Adapted from NREL ATB 2021 .. wind speed (m/s)
    if windSpeed100 > 9.0:
        windClass = 1
    elif windSpeed100 >= 8.8:
        windClass = 2
    elif windSpeed100 >= 8.6:
        windClass = 3
    elif windSpeed100 >= 8.4:
        windClass = 4
    elif windSpeed100 >= 8.1:
        windClass = 5
    elif windSpeed100 >= 7.6:
        windClass = 6
    elif windSpeed100 >= 7.1:
        windClass = 7
    elif windSpeed100 >= 6.5:
        windClass = 8
    elif windSpeed100 >= 5.9:
        windClass = 9
    else:
        windClass = 10

    return lat, lon, windSpeed100, windClass


def getWindCosts():
    """Load NREL ATB data for access to future cost projections (2021-2035)"""

    atb_path = os.path.join(local_path, 'ATB/ATB2021.csv')
    atb = pd.read_csv(atb_path)

    wind_atb = atb[['TECH', 'YEAR', 'CAPEX_($/MW)', 'FOPEX_($/MW)']]

    wind_atb = wind_atb[wind_atb['TECH'] == 'Wind']
    del wind_atb['TECH']

    convert_dict = {'YEAR': int,
                    'CAPEX_($/MW)': float,
                    'FOPEX_($/MW)': float
                    }

    wind_atb = wind_atb.astype(convert_dict).reset_index(drop=True)

    print(wind_atb)
    print(wind_atb.dtypes)

    return wind_atb


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


def mergeData():
    year = args.data_year
    timespan = range(2021, 2031)

    wind_atb = getWindCosts()

    print(getCoords())
    coords = getCoords()
    print(f'{len(coords)} coordinates found...')

    data = []
    for i in range(len(coords)):
        lat = coords[i][0]
        lon = coords[i][1]

        data.append(getWindData(year, lat, lon))

    windCosts = pd.DataFrame(data, columns=('lat', 'lon', 'windSpeed', 'windClass'))

    for y in timespan:
        if y == 2021:
            windCosts.loc[:, 'CAPEX_($/MW)_2021'] = wind_atb.iloc[0]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2021'] = wind_atb.iloc[0]['FOPEX_($/MW)']

        elif y == 2022:
            windCosts.loc[:, 'CAPEX_($/MW)_2022'] = wind_atb.iloc[1]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2022'] = wind_atb.iloc[1]['FOPEX_($/MW)']

        elif y == 2023:
            windCosts.loc[:, 'CAPEX_($/MW)_2023'] = wind_atb.iloc[2]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2023'] = wind_atb.iloc[2]['FOPEX_($/MW)']

        elif y == 2024:
            windCosts.loc[:, 'CAPEX_($/MW)_2024'] = wind_atb.iloc[3]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2024'] = wind_atb.iloc[3]['FOPEX_($/MW)']

        elif y == 2025:
            windCosts.loc[:, 'CAPEX_($/MW)_2025'] = wind_atb.iloc[4]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2025'] = wind_atb.iloc[4]['FOPEX_($/MW)']

        elif y == 2026:
            windCosts.loc[:, 'CAPEX_($/MW)_2026'] = wind_atb.iloc[5]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2026'] = wind_atb.iloc[5]['FOPEX_($/MW)']

        elif y == 2027:
            windCosts.loc[:, 'CAPEX_($/MW)_2027'] = wind_atb.iloc[6]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2027'] = wind_atb.iloc[6]['FOPEX_($/MW)']

        elif y == 2028:
            windCosts.loc[:, 'CAPEX_($/MW)_2028'] = wind_atb.iloc[7]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2028'] = wind_atb.iloc[7]['FOPEX_($/MW)']

        elif y == 2029:
            windCosts.loc[:, 'CAPEX_($/MW)_2029'] = wind_atb.iloc[8]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2029'] = wind_atb.iloc[8]['FOPEX_($/MW)']

        else:
            windCosts.loc[:, 'CAPEX_($/MW)_2030'] = wind_atb.iloc[9]['CAPEX_($/MW)']
            windCosts.loc[:, 'FOPEX_($/MW)_2030'] = wind_atb.iloc[9]['FOPEX_($/MW)']

    return windCosts


def main():
    print(f'local path: {local_path}')  # quick check

    windCosts = mergeData()

    out_path = os.path.join(local_path, 'wind_data_output/wind_costs.csv')

    windCosts.to_csv(out_path, index=False)

    print('That\'s all folks!')


if __name__ == '__main__':
    main()
