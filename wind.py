import pandas as pd
import numpy as np
import argparse
import geopandas as gpd
from shapely.geometry import Point
import os

local_path = os.path.dirname(os.path.abspath(__file__))

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--year', type=int, choices=[2010, 2011, 2012, 2013, 2014], help='Data year. Must be in '
                                                                                     '2010-2014 (inclusive).',
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
# Following arguments needed when running in PyCharm
parser.add_argument("--mode", default='client')
parser.add_argument("--port", default=50071)  # change port default as needed

args = parser.parse_args()


def getWindData(year, lat, lon):
    """ by year and coordinate --> retrieves wind resource data from NREL's WIND Toolkit and ATB 2020 """

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

    # Adapted from NREL ATB 2020 .. wind speed (m/s), CAPEX ($/MW)
    if windSpeed100 >= 9.01:
        windClass = 1
        CAPEX = 1642020
    elif windSpeed100 >= 8.77:
        windClass = 2
        CAPEX = 1523730
    elif windSpeed100 >= 8.57:
        windClass = 3
        CAPEX = 1492620
    elif windSpeed100 >= 8.35:
        windClass = 4
        CAPEX = 1483590
    elif windSpeed100 >= 8.07:
        windClass = 5
        CAPEX = 1522560
    elif windSpeed100 >= 7.62:
        windClass = 6
        CAPEX = 1665030
    elif windSpeed100 >= 7.1:
        windClass = 7
        CAPEX = 1830930
    elif windSpeed100 >= 6.53:
        windClass = 8
        CAPEX = 2168570
    elif windSpeed100 >= 5.9:
        windClass = 9
        CAPEX = 2548910
    elif windSpeed100 >= 1.72:
        windClass = 10
        CAPEX = 2690060
    else:
        windClass = 'NA'
        CAPEX = 'NA'

    return lat, lon, windSpeed100, windClass, CAPEX


def getCoords():
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

    min_lon = round(bounds[0], 3)
    min_lat = round(bounds[1], 3)
    max_lon = round(bounds[2], 3)
    max_lat = round(bounds[3], 3)

    lat = min_lat

    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            if statesShp.contains(Point(lon, lat)).any():
                coordinates.append((lat, lon))
            lon += args.deg_resolution
        lat += args.deg_resolution

    return coordinates


def main():
    print(f'local path: {local_path}')
    print(getCoords())

    year = args.year
    coords = getCoords()
    print(f'{len(coords)} coordinates found...')

    data = []
    for i in range(len(coords)):
        lat = coords[i][0]
        lon = coords[i][1]
        print(getWindData(year, lat, lon))

        data.append((getWindData(year, lat, lon)))

    windCosts = pd.DataFrame(data, columns=('lat', 'lon', 'windSpeed', 'windClass', 'CAPEX'))

    # Value based on NREL ATB 2020 and Lazard v14.0 reports
    windCosts.loc[:, 'FOPEX'] = 40 * (10**3)  # $/MW-yr

    # Output
    out_path = os.path.join(local_path, 'wind_data_output/wind_costs.csv')
    windCosts.to_csv(out_path, index=False)

    print('finished!')


if __name__ == '__main__':
    main()
