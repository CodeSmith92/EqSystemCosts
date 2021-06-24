import pandas as pd
import numpy as np
import argparse
import geopandas as gpd
from shapely.geometry import Point
import os

parser = argparse.ArgumentParser(description='Download wind and solar resource data, then use PySAM to convert to '
                                             'hourly capacity factors.')
parser.add_argument('--year', type=int, choices=[2010, 2011, 2012, 2013, 2014], help='Data year. Must be in '
                                                                                     '2010-2014 (inclusive).')
parser.add_argument('--api_key', type=str, help='NREL API Key. Sign up @ '
                                                'https://developer.nrel.gov/signup/',
                    default='qgjZ5sr5MHoI26rC69QfLhIM9T5xsRGHwPiGWi8j')
parser.add_argument('--email', type=str, help='Email address.', default='dcorrell@umich.edu')
parser.add_argument('--save_resource', help='Save resource data in addition to generation data, THIS COULD TAKE A LOT '
                                            'OF DISK SPACE', action='store_true')
parser.add_argument('--verbose', action='store_true')
parser.add_argument('--lat', type=float, help='Required if geometry=point')
parser.add_argument('--lon', type=float, help='Required if geometry=point')
parser.add_argument('--min_lat', type=float)
parser.add_argument('--max_lat', type=float)
parser.add_argument('--min_lon', type=float)
parser.add_argument('--max_lon', type=float)
parser.add_argument('--states', nargs='+', type=str, help='Required if geometry=state, e.g. \'PA OH NY\'')
parser.add_argument('--deg_resolution', type=float, default=.04, help='Approximate km resolution of grid. Used for '
                                                                      'geometry=state or geometry=grid, default .04')

args = parser.parse_args()
user_name = 'mr_smith'
path = f'/Users/{user_name}/Desktop/'
local_path = os.path.dirname(__file__)


def getWindCAPEX(year, states):
    """ calculate land-based wind capital expenditure (CAPEX) based on geographic location (average wind speed) """

    windSRW = os.path.join(local_path, 'resourceData/{lat}_{lon}_wtk.srw'.format(lat=lat, lon=lon))

    if not os.path.exists(windSRW):
        wtk_url = 'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download'

        params = {'api_key': args.api_key,
                  'email': args.email,
                  'lat': lat,
                  'lon': lon,
                  'hubheight': 100,
                  'year': year,
                  'utc': 'true'
                  }

        params_str = '&'.join(['{key}={value}'.format(key=key, value=params[key]) for key in params])
        download_url = '{wtk_url}?{params_str}'.format(wtk_url=wtk_url, params_str=params_str)

        windResource = pd.read_csv(download_url)

        # Process for SAM
        windResourceDescription = windResource.columns.values.tolist()

        # Save srw
        windResource.to_csv(windSRW, index=False)

    # Find wind speed
    windSpeed100 = np.median(pd.read_csv(windSRW, skiprows=[0, 1, 3, 4], usecols=['Speed']).values)

    # Adapted from NREL ATB 2020
    if windSpeed100 >= 9.01:
        windClass = 1
    elif windSpeed100 >= 8.77:
        windClass = 2
    elif windSpeed100 >= 8.57:
        windClass = 3
    elif windSpeed100 >= 8.35:
        windClass = 4
    elif windSpeed100 >= 8.07:
        windClass = 5
    elif windSpeed100 >= 7.62:
        windClass = 6
    elif windSpeed100 >= 7.1:
        windClass = 7
    elif windSpeed100 >= 6.53:
        windClass = 8
    elif windSpeed100 >= 5.9:
        windClass = 9
    elif windSpeed100 >= 1.72:
        windClass = 10
    else:
        windClass = 'NA'

    # TODO: add CAPEX values to column based on wind-class

    # Local file output
    windClassOUT = os.path.join(path, 'windClassOUT.csv')
    windSRW.to_csv(windClassOUT, index=False)

    return windSRW, windClass


def getStateCoords():

    states = ['AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'ID', 'IL',
              'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO',
              'MT', 'NE', 'NV', 'NH', 'NH', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR',
              'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI',
              'WY']
    for state in args.states:
        if state in states:
            # get outer bounds
            usShp = gpd.read_file(os.path.join(local_path, 'states/s_11au16.shp'))
            statesShp = usShp[usShp['STATE'].isin(states)]
            bounds = statesShp.total_bounds

            coordinates = []

            bounds = statesShp.total_bounds
            min_lon = round(bounds[0], 2)
            min_lat = round(bounds[1], 2)
            max_lon = round(bounds[2], 2)
            max_lat = round(bounds[3], 2)
            lat = min_lat
            print(lat)
            while lat <= max_lat:
                lon = min_lon
                while lon <= max_lon:
                    if statesShp.contains(Point(lon, lat)).any():
                        coordinates.append((lat, lon))
                    lon += args.deg_resolution
                lat += args.deg_resolution

            return coordinates


def main():
    print(getStateCoords())


if __name__ == '__main__':
    main()
