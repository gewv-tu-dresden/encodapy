"""
Main file so start the example service with new component using component_runner
"""

import asyncio

from service_main.main import main


if __name__ == "__main__":
    asyncio.run(main())
