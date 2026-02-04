"""
Main file to start the example service
"""

import asyncio

from dotenv import load_dotenv
from example_service import ExampleService

from encodapy.service.service_main import service_main

if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    asyncio.run(service_main(service_class=ExampleService))
