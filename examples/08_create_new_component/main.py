"""
Main file so start the example service with new component using component_runner
"""

import asyncio

from encodapy.service.service_main import service_main

if __name__ == "__main__":
    asyncio.run(service_main())
