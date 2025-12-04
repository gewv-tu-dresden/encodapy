"""
Main file so start the example service
"""

import asyncio

from thermal_storage_service import ThermalStorageService

from encodapy.service.service_main import service_main

if __name__ == "__main__":
    asyncio.run(service_main(service_class=ThermalStorageService))
