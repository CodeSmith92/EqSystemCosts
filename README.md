# EqSystemCosts

Program for extracting annual coal plant generation and related data; for calculating each coal plant's annual operating costs (FOPEX ($/MW-yr) and VOPEX ($/MWh)); and for calculating the capital and operational costs (CAPEX ($/MW) and FOPEX ($/MW-yr)) of wind and solar power. The file 'coal.py' relies primarily on data input from the Energy Information Administration form EIA-923. 

## Updates 

* 07/23/2021
> Added '--year' argument (2015-2020 inclusive) to coal.py --> returns FOPEX ($/MW-yr) and VOPEX ($/MWh) values for operational coal plants (based on EIA-923 data)

## Planned updates
- [ ] Incorporate discounting

## Setup
1. Get an [NREL API Key](https://developer.nrel.gov/signup/):
> Only necesarry for 'wind.py' and 'solar.py'

2. Install dependencies:

        pip install numpy
        pip install pandas
        pip install geopandas
        pip install argparse
        pip install shapely
       
        
3. Clone repository:

        git clone https://github.com/CodeSmith92/EqSystemCosts.git


## CLI: Coal

When running from the command line, terminal, or shell, the '--year' parameter must be passed as a key-value pair. For example:

    python coal.py --year 2020



| Key   | Type | Options | Required | Description|
| ----- | ---- | --------| -------- | ---------- |
| `year`  | int  | 2015-2020| Yes     | Inclusive  |


## CLI: Wind and Solar

| Key   | Type | Options | Required | Description|
| ----- | ---- | --------| -------- | ---------- |
| `year`  | int  | 2010-2014 (wind); 2016-2020 (solar) | Yes     | Inclusive  |
| `api_key` | str |         | Yes     |            |
| `email`  | str  |         | Yes     |            |
| `geometry` | str | `grid`, `state` | Yes | RE site options --> `grid`: Every point in a grid from a min lat/lon to a max lat/lon. `state`: Grid bounded by one or multiple states.|
| `min_lat`   | float |         | If `grid` |            |
| `min_lon`   | float |         | If `grid` |            |
| `max_lat`   | float |         | If `grid` |            |
| `max_lon`   | float |         | If `grid` |            |
| `states`    | str |        | If `state` | Choose states in which to build wind farms and/or solar parks... e.g. 'NJ NY' (for New Jersey and New York).. Input == 'CONTINENTAL' for entire US. |
| `deg_resolution` | float | >.04| If `grid` or `state` | Lat/lon resolution (in degrees). **Default:** .04 |

Example:

    python wind.py --year 2014 --api_key <my-key> --email <my-email> --geometry state --deg_resolution .5 --states NJ NY CT PA DE VA


### Data sources:

1. [Wind Resource Data](https://www.nrel.gov/grid/wind-toolkit.html) [1-4]

2. [Solar Radiation Data](https://nsrdb.nrel.gov/) [5]

3. [State shapefiles](https://www.weather.gov/gis/USStates) [6]
 
4. [EIA-923](https://www.eia.gov/electricity/data/eia923/)

### EIA-923
>"The survey Form EIA-923 collects detailed electric power data -- monthly and annually -- on electricity generation, fuel consumption, fossil fuel stocks, and receipts at the power plant and prime mover level."

## Citations
[1] Draxl, C., B.M. Hodge, A. Clifton, and J. McCaa. 2015. Overview and Meteorological Validation of the Wind Integration National Dataset Toolkit (Technical Report, NREL/TP-5000-61740). Golden, CO: National Renewable Energy Laboratory.

[2] Draxl, C., B.M. Hodge, A. Clifton, and J. McCaa. 2015. "The Wind Integration National Dataset (WIND) Toolkit." Applied Energy 151: 355366.

[3] Lieberman-Cribbin, W., C. Draxl, and A. Clifton. 2014. Guide to Using the WIND Toolkit Validation Code (Technical Report, NREL/TP-5000-62595). Golden, CO: National Renewable Energy Laboratory.

[4] King, J., A. Clifton, and B.M. Hodge. 2014. Validation of Power Output for the WIND Toolkit (Technical Report, NREL/TP-5D00-61714). Golden, CO: National Renewable Energy Laboratory.

[5] Sengupta, M., Y. Xie, A. Lopez, A. Habte, G. Maclaurin, and J. Shelby. 2018. "The National Solar Radiation Data Base (NSRDB)." Renewable and Sustainable Energy Reviews  89 (June): 51-60.

[6] National Weather Service. 2016. U.S. States and Territories Shapefile.
