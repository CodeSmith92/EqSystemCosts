import pandas as pd
import argparse
import geopandas as gpd
from shapely.geometry import Point
import os

local_path = os.path.dirname(os.path.abspath(__file__))

# CLI arguments
parser = argparse.ArgumentParser(description='Command line arguments for data extraction and cost calculations')
parser.add_argument('--year', type=int, choices=[2016, 2017, 2018, 2019, 2020], help='Data year. Must be in '
                                                                                     '2016-2020 (inclusive).',
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


def getSolarData(year, lat, lon):

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
        print(getSolarData(year, lat, lon))

        data.append((getSolarData(year, lat, lon)))

    solarCosts = pd.DataFrame(data, columns=('lat', 'lon', 'nsrdbLat', 'nsrdbLon', 'elevation'))

    # Value based on NREL ATB 2020 and Lazard v14.0 reports
    solarCosts.loc[:, 'FOPEX'] = 15 * (10**3)  # $/MW-yr
    solarCosts.loc[:, 'CAPEX'] = 1300000  # $/MW

    # Output
    out_path = os.path.join(local_path, 'solar_data_output/solar_costs.csv')
    solarCosts.to_csv(out_path, index=False)

    print('Finished!')


if __name__ == '__main__':
    main()

