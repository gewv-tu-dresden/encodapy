"""
Main file so start the example service
"""

import asyncio
from example_service import ExampleService
from encodapy.service import service_main

if __name__ == "__main__":
    asyncio.run(service_main(service_class=ExampleService))
