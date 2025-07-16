"""
Main file so start the pb controller service
"""

import asyncio
from asyncio.tasks import sleep

from dotenv import load_dotenv

from pb_controller import PBController


async def main():
    """
    Main function to start the example service
        - prepare the start of the service
        - start the calibration
        - start the service
    """

    service = PBController()

    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_start_service = asyncio.create_task(service.start_service())

    service_tasks = [task_for_calibration, task_for_start_service]

    await asyncio.gather(*service_tasks)

    while True:
        await sleep(0.1)


if __name__ == "__main__":
    LOADED_ENV = load_dotenv(".env")
    print(f"Loaded env: {LOADED_ENV}")
    asyncio.run(main())
