"""
Main file so start the example service
"""
import asyncio
from asyncio.tasks import sleep

from thermal_storage_service import ThermalStorageService


async def main():
    """
    Main function to start the example service

        - start the calibration
        - start the health check
        - start the service
    """

    service = ThermalStorageService()

    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_check_health = asyncio.create_task(service.check_health_status())
    task_for_start_service = asyncio.create_task(service.start_service())

    await asyncio.gather(task_for_calibration,
                         task_for_check_health,
                         task_for_start_service)

    while True:
        await sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
