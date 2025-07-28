"""
Main file so start the example service
"""

import asyncio
from asyncio.tasks import sleep

from dotenv import load_dotenv
from mqtt_coupler_trnsys import MQTTCouplerTrnsys


async def main():
    """
    Main function to start the example service
        - prepare the start of the service
        - start the calibration
        - start the service
    """

    service = MQTTCouplerTrnsys()

    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_start_service = asyncio.create_task(service.start_service())

    await asyncio.gather(task_for_calibration, task_for_start_service)

    while True:
        await sleep(0.1)


if __name__ == "__main__":
    LOADED_ENV = load_dotenv(".env")
    print(f"Loaded env: {LOADED_ENV}")
    asyncio.run(main())
