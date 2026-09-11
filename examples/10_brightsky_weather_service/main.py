"""
Main file so start the example service with new component using component_runner
"""

import asyncio

from dotenv import load_dotenv

from weather_data import WeatherService

from encodapy.service.service_main import service_main

load_dotenv()

if __name__ == "__main__":
    asyncio.run(service_main(service_class=OpenWeatherMapService))

