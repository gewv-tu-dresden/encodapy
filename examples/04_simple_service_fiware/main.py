"""
Main file so start the example service
"""
import asyncio
from dotenv import load_dotenv
from example_service import ExampleService
from service_main.main import main

if __name__ == "__main__":
    load_dotenv()  # Load environment variables from .env file
    asyncio.run(main(service_class=ExampleService))
