"""
Main file so start the base service
"""
import asyncio
from asyncio.tasks import sleep

from encodapy.service.basic_service import ControllerBasicService


async def main():
    """
    Main function to start the base service
        - start the calibration
        - start the health check
        - start the service
    """

    service = ControllerBasicService()

    task_calibration = asyncio.create_task(service.start_calibration())
    task_check_health = asyncio.create_task(service.check_health_status())
    task_start_service = asyncio.create_task(service.start_service())

    await asyncio.gather(task_calibration, task_check_health, task_start_service)

    while True:
        await sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())
