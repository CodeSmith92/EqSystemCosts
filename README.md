# EqSystemCosts

Program for extracting annual coal plant generation and related data; for calculating each coal plant's annual operating costs; and for calculating the capital and operational costs of wind and solar power. Relies on data input from EIA-923 (2015-present). 

## Updates 

* 07/23/2021
> added 'year' argument (2015-2020 inclusive) to coal.py --> returns FOPEX and VOPEX values for operational coal plants (based on EIA-923 data)

### TODO: 

> DOCUMENTATION HERE


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
