"""
Main file so start the example service
"""

import asyncio
import os
import signal
from typing import Type, cast

from loguru import logger

from encodapy.service.basic_service import ControllerBasicService
from encodapy.service.component_runner_service import ComponentRunnerService


async def service_main(service_class: Type[ControllerBasicService] = ComponentRunnerService):
    """
    Main function to start the example service

        - start the calibration
        - start the health check
        - start the service
    Args:
        service_class (Type[ControllerBasicService]): \
            The service class to be started, defaults to ComponentRunnerService

    The service class should have an optional parameter `shutdown_event` in the constructor \
        to handle shutdown events.
    """

    shutdown_event = asyncio.Event()
    try:
        service = service_class(shutdown_event=shutdown_event)
    except TypeError:
        # if the service_class does not have the shutdown_event parameter
        # for backward compatibility, it is recommended to add it
        service = service_class()
        logger.warning(
            "The service_class does not support the shutdown_event parameter. "
            "Please update the service_class to support it for proper shutdown."
        )

    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_check_health = asyncio.create_task(service.check_health_status())
    task_for_start_service = asyncio.create_task(service.start_service())

    def signal_handler():
        """Handler for SIGTERM and SIGINT signals"""
        logger.debug("Shutdown signal received, end service properly...")
        shutdown_event.set()

    try:
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())

        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    except (OSError, AttributeError) as e:
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        logger.debug(f"Only SIGINT handler registered: {e}")

    try:
        service_tasks: list[asyncio.Task] = [
            task_for_check_health,
            task_for_calibration,
            task_for_start_service,
        ]

        shutdown_task = asyncio.create_task(shutdown_event.wait())
        main_gather = asyncio.gather(*service_tasks, return_exceptions=True)

        await asyncio.wait(
            [cast(asyncio.Task, main_gather), shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if service_tasks:
            try:
                done, pending = await asyncio.wait(
                    service_tasks, timeout=30.0, return_when=asyncio.ALL_COMPLETED
                )

                if pending:
                    logger.error(
                        "Service could not be terminated properly: "
                        f"{len(pending)} Tasks hang."
                    )
                    logger.debug(f"Some tasks successfully finished: {len(done)}")

                    raise TimeoutError(
                        "Service could not be terminated properly: "
                        f"{len(pending)} Tasks hang."
                    )
            except Exception as e:
                logger.error(f"Error when exiting the service: {e}")
                raise

        logger.info("Service successfully stopped")

    except Exception as e:
        logger.error(f"Error when exiting or executing the service: {e}")

        if isinstance(e, TimeoutError):
            logger.warning("Forcing process exit due to hanging tasks")
            os._exit(1)
        raise


if __name__ == "__main__":
    asyncio.run(service_main())
