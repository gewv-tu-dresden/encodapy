"""
Main file so start the example service with new component using component_runner
"""

import asyncio

from dotenv import load_dotenv

from encodapy.service import service_main

load_dotenv()
print(f"Loaded env: {load_dotenv()}")

if __name__ == "__main__":
    asyncio.run(service_main())
