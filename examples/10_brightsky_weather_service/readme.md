# Component Weather Data

## Overview

Example of the use of the weather data component in EnCoDaPy. 

- [config.json](./config.json): Configuration for the service - see [01_config](./../01_config/)
- [run_weatherdata_service.ipynb](./run_weatherdata_service.ipynb): Notebook to run the service (you can also run [encodapy.service.service_main](./../../encodapy/service/service_main.py))

## Usage

To run the example, you need to add a [.env](.env):

```
CONFIG_PATH = "./config.json"               #  path of the file for the config
PATH_OF_STATIC_DATA = "./static_data.json"  #  path of the file for the static_data
PATH_OF_RESULTS = "./results"               #  if interface file is used, name/path of the results_file
```


