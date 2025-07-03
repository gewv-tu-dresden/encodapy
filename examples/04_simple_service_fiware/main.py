"""
Main file so start the example service
"""
import asyncio
import signal
import os
from loguru import logger
from example_service import ExampleService


async def main():
    """
    Main function to start the example service
        - start the calibration
        - start the health check
        - start the service
    Possibilitie to stop the service with SIGINT or SIGTERM
    """

    service = ExampleService()

    task_for_check_health = asyncio.create_task(service.check_health_status())
    task_for_calibration = asyncio.create_task(service.start_calibration())
    task_for_start_service = asyncio.create_task(service.start_service())


    shutdown_event = asyncio.Event()

    def signal_handler():
        """Handler für SIGTERM und SIGINT Signale"""
        logger.debug("Shutdown signal received, end service properly...")
        shutdown_event.set()

    try:

        signal.signal(signal.SIGINT, lambda s, f: signal_handler())

        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        logger.debug("Signal handlers registered: SIGINT, SIGTERM")
    except (OSError, AttributeError) as e:

        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        logger.debug(f"Only SIGINT handler registered: {e}")

    try:

        service_tasks = [task_for_check_health, task_for_calibration, task_for_start_service]

        main_gather = asyncio.gather(*service_tasks, return_exceptions=True)
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        await asyncio.wait(
            [main_gather, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        logger.debug("Finish all tasks...")
        for task in service_tasks:
            if not task.done():
                task.cancel()


        if service_tasks:
            try:
                done, pending = await asyncio.wait(
                    service_tasks,
                    timeout=10.0,
                    return_when=asyncio.ALL_COMPLETED
                )
                if pending:
                    logger.error("Service could not be terminated properly: "
                                 f"{len(pending)} Tasks hang.")
                    logger.debug(f"Some tasks successfully finished: {len(done)}")

                    raise TimeoutError("Service could not be terminated properly: "
                                       f"{len(pending)} Tasks hang.")
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
    asyncio.run(main())
