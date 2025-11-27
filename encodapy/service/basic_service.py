"""
Module for the basic service class for the data processing and transfer via different interfaces.
Author: Martin Altenburger
"""
import sys
from datetime import datetime
from typing import Optional, Union
import asyncio
from loguru import logger
from pydantic import ValidationError

from encodapy.config import (
    AttributeModel,
    CommandModel,
    ConfigModel,
    DataQueryTypes,
    Interfaces,
    OutputModel,
    BasicEnvVariables
)
from encodapy.service.communication import (
    FileConnection,
    FiwareConnection,
    MqttConnection,
)
from encodapy.utils.error_handling import ConfigError, InterfaceNotActive
from encodapy.utils.health import update_health_file
from encodapy.utils.logging import LoggerControl
from encodapy.utils.models import (
    DataTransferComponentModel,
    DataTransferModel,
    InputDataModel,
    OutputDataEntityModel,
    OutputDataModel,
    StaticDataEntityModel,
)
from encodapy.utils.units import get_time_unit_seconds


class ControllerBasicService(FiwareConnection, FileConnection, MqttConnection):
    """
    Class for processing the data transfer to different connections
    and start a function to do the calculations.

    """

    def __init__(self, shutdown_event: Optional[asyncio.Event] = None) -> None:
        FiwareConnection.__init__(self)
        FileConnection.__init__(self)
        MqttConnection.__init__(self)

        self.shutdown_event = shutdown_event or asyncio.Event()
        self.env: BasicEnvVariables = BasicEnvVariables()
        self.logger = LoggerControl(log_level=self.env.log_level)

        self.staticdata: Optional[list[StaticDataEntityModel]] = None

        self.timestamp_health = None

        self.prepare_basic_start()

    def _load_config(self):
        """
        Function loads the environemtal variables and the config of the service.

        """

        try:
            self.config = ConfigModel.from_json(file_path=self.env.config_path)
        except (
            FileNotFoundError,
            ValidationError,
            ConfigError,
            InterfaceNotActive,
        ) as e:
            logger.error(f"Error loading configuration file: {e}")
            sys.exit(1)

        if self.config.interfaces.fiware:
            self.load_fiware_params()

        if self.config.interfaces.file:
            self.load_file_params()

        if self.config.interfaces.mqtt:
            self.load_mqtt_params()

        logger.debug("Config succesfully loaded.")


    def prepare_basic_start(self):
        """
        Function to create important objects with the configuration from the configuration
        file (.env) and prepare the start basics of the service.
        """
        logger.info("Prepare the basic start of the service")

        self._load_config()

        interfaces = getattr(self.config, "interfaces", None)
        if interfaces:
            if getattr(interfaces, "fiware", False):
                self.prepare_fiware_connection()

            if getattr(interfaces, "mqtt", False):
                self.prepare_mqtt_connection()

        # Load the static data from the configuration, \
        # maybe it is needed for the preparation of components
        try:
            self.staticdata = self.reload_static_data(
                method=DataQueryTypes.CALIBRATION, staticdata=[]
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error reloading static data: {e}")
            self.cleanup_service()
            raise

        # Prepare the individual start of the service
        try:
            self.prepare_start()
        except (KeyError, ValueError, TypeError, ValidationError) as e:
            logger.error(f"Error preparing the start of the service: {e}")
            self.cleanup_service()
            raise

    def prepare_start(self):
        """
        Function prepare the specific aspects of the start of the service \
            Fuction is called by the function for the basic preparing

        This function can be overwritten in the specific service.
        
        The function should not be do anything time consuming, \
            because the health check is not running yet.

        """
        logger.debug("There is nothing else to prepare for the start of the service.")

    def reload_static_data(
        self, method: DataQueryTypes, staticdata: list
    ) -> list[StaticDataEntityModel]:
        """
        Function to reload the static data
        Args:
            method (DataQueryTypes): method for the data query
            staticdata (list): list of static data
        Returns:
            list: list of static data
        """
        if len(self.config.staticdata) == 0:
            return []

        for static_entity in self.config.staticdata:
            if static_entity.interface == Interfaces.FIWARE:
                staticdata.append(
                    StaticDataEntityModel(
                        **self.get_data_from_fiware(
                            method=method,
                            entity=static_entity,
                            timestamp_latest_output=None,
                        ).model_dump()
                    )
                )

            if static_entity.interface == Interfaces.FILE:
                staticdata.append(
                    StaticDataEntityModel(
                        **self.get_staticdata_from_file(
                            entity=static_entity,
                        ).model_dump()
                    )
                )

            if static_entity.interface == Interfaces.MQTT:
                logger.warning("interface MQTT for staticdata not supported")

        return staticdata

    async def get_data(self, method: DataQueryTypes) -> InputDataModel:
        """
        Function to get the data of all input entities via the different interfaces
        (FIWARE, FILE, MQTT)

        Args:
            method (DataQueryTypes): Method for the data query

        Returns:
            InputDataModel: Model with the input data

        """

        input_data = []
        output_timestamps = []
        output_latest_timestamps = []

        if self.config is None:
            logger.error(
                "Configuration is not loaded. Please call prepare_start() first."
            )
            return InputDataModel(
                input_entities=[], output_entities=[], static_entities=[]
            )

        for output_entity in self.config.outputs:
            if output_entity.interface == Interfaces.FIWARE:
                entity_timestamps, output_latest_timestamp = (
                    self._get_last_timestamp_for_fiware_output(output_entity)
                )

                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)

            elif output_entity.interface == Interfaces.FILE:
                entity_timestamps, output_latest_timestamp = (
                    self._get_last_timestamp_for_file_output(output_entity)
                )
                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)
                logger.debug("File interface, output_latest_timestamp is not defined.")

            elif output_entity.interface == Interfaces.MQTT:
                entity_timestamps, output_latest_timestamp = (
                    self._get_last_timestamp_for_mqtt_output(output_entity)
                )
                output_timestamps.append(entity_timestamps)
                output_latest_timestamps.append(output_latest_timestamp)

            await asyncio.sleep(0.01)

        if None in output_latest_timestamps:
            output_latest_timestamp = None
        else:
            if len(output_latest_timestamps) > 0:
                output_latest_timestamp = min(output_latest_timestamps)
            else:
                output_latest_timestamp = None

        for input_entity in self.config.inputs:
            if input_entity.interface == Interfaces.FIWARE:
                fiware_input = self.get_data_from_fiware(
                    method=method,
                    entity=input_entity,
                    timestamp_latest_output=output_latest_timestamp,
                )
                if fiware_input is not None:
                    input_data.append(fiware_input)

            elif input_entity.interface == Interfaces.FILE:
                file_input = self.get_data_from_file(method=method, entity=input_entity)
                if file_input is not None:
                    input_data.append(file_input)

            elif input_entity.interface == Interfaces.MQTT:
                input_data.append(
                    self.get_data_from_mqtt(
                        method=method,
                        entity=input_entity,
                    )
                )

            await asyncio.sleep(0.01)

        if self.env.reload_staticdata or self.staticdata is None:
            self.staticdata = self.reload_static_data(method=method, staticdata=[])

        return InputDataModel(
            input_entities=input_data,
            output_entities=output_timestamps,
            static_entities=self.staticdata,
        )

    def _get_output_entity_config(
        self,
        output_entity_id: str,
    ) -> Union[OutputModel, None]:
        """
        Function to get the configuration of the output attributes

        Args:
            - output_entity: id of the output entity

        Returns:
            - Union[OutputModel, None]: configuration of the output entity
            or None if the entity is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:
                return entity

        return None

    def _get_output_attribute_config(
        self,
        output_entity_id: str,
        output_attribute_id: str,
    ) -> Union[AttributeModel, None]:
        """
        Function to get the configuration of the output attribute

        Args:
            - output_entity: id of the output entity
            - output_attribute: id of the output attribute

        Returns:
            - Union[AttributeModel, None]: configuration of the output attribute
            or None if the attribute is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:
                for attribute in entity.attributes:
                    if attribute.id == output_attribute_id:
                        return attribute

        return None

    def _get_output_command_config(
        self,
        output_entity_id: str,
        output_command_id: str,
    ) -> Union[CommandModel, None]:
        """
        Function to get the configuration of the output attribute

        Args:
            - output_entity: id of the output entity
            - output_attribute: id of the output attribute

        Returns:
            - Union[AttributeModel, None]: configuration of the output attribute
            or None if the attribute is not found
        """
        for entity in self.config.outputs:
            if entity.id == output_entity_id:
                for commmand in entity.commands:
                    if commmand.id == output_command_id:
                        return commmand

        return None

    async def send_outputs(self, data_output: Union[OutputDataModel, None]):
        """
        Send output data to the interfaces defined in the Config (FIWARE, MQTT, File)

        Args:
            - data_output: OutputDataModel with the output data

        TODO: - Implement a way to use different interfaces (MQTT)
        """

        if data_output is None:
            logger.debug("No data for sending out to  instance (FIWARE, MQTT, FILE)")
            return

        for output in data_output.entities:
            output_entity = self._get_output_entity_config(output_entity_id=output.id)
            output_attributes = []
            output_commands = []

            if output_entity is None:
                logger.debug(f"Output entity {output.id} not found in configuration.")
                continue

            for attribute in output.attributes:
                output_attribute = self._get_output_attribute_config(
                    output_entity_id=output.id, output_attribute_id=attribute.id
                )

                if output_attribute is None:
                    logger.debug(
                        f"Output attribute {attribute.id} not found in configuration."
                    )
                    continue

                output_attribute.value = attribute.value
                output_attribute.unit = attribute.unit
                output_attribute.timestamp = attribute.timestamp
                output_attributes.append(output_attribute)

            for command in output.commands:
                output_command = self._get_output_command_config(
                    output_entity_id=output.id, output_command_id=command.id
                )

                if output_command is None:
                    logger.debug(
                        f"Output attribute {command.id} not found in configuration."
                    )
                    continue

                output_command.value = command.value
                output_commands.append(output_command)

            if output_entity.interface is Interfaces.FIWARE:
                await self._send_data_to_fiware(
                    output_entity=output_entity,
                    output_attributes=output_attributes,
                    output_commands=output_commands,
                )

            elif output_entity.interface is Interfaces.FILE:
                self.send_data_to_json_file(
                    output_entity=output_entity,
                    output_attributes=output_attributes,
                    output_commands=output_commands,
                )

            elif output_entity.interface is Interfaces.MQTT:
                self.send_data_to_mqtt(
                    output_entity=output_entity,
                    output_attributes=output_attributes,
                )

            await asyncio.sleep(0.01)

        logger.debug("Finished sending output data")

    async def _hold_sampling_time(
        self, start_time: datetime, hold_time: Union[int, float]
    ):
        """
        Wait in each cycle until the sampling time (or cycle time) is up. If the algorithm takes
        more time than the sampling time, a warning will be given.
        Args:
            start_time: datetime, start time of the cycle
            hold_time: int or float, sampling time in seconds
        """
        if ((datetime.now() - start_time).total_seconds()) > hold_time:
            logger.warning(
                "The processing time is longer than the sampling time."
                "The sampling time must be increased!"
            )
        while ((datetime.now() - start_time).total_seconds()) < hold_time:
            if self.shutdown_event.is_set():
                break
            await asyncio.sleep(0.01)

    async def calculation(
        self,
        data: InputDataModel,
    ) -> Union[DataTransferModel, None]:
        """
        Function to start the calculation, do something with data - used in the services
        Only a dummy function, has to be implemented in the services
        Args:
            - data: InputDataModel with the input data
        Returns:
            - Union[DataTransferModel, None]: Output data from the calculation
        """
        logger.debug(
            "No calculation function implemented, "
            f"get the data only: {data.model_dump_json()}"
        )
        return None

    async def calibration(self, data: InputDataModel):
        """
        Function to start the calibration, do something with data - used in the services
        Only a dummy function, has to be implemented in the services
        """

        logger.debug(
            "No calibration function implemented, "
            f"get the data only: {data.model_dump_json()}"
        )
        return None

    def prepare_output(self, data_output: DataTransferModel) -> OutputDataModel:
        """
        Function to prepare the output data for the different interfaces (FIWARE, FILE, MQTT)
        Takes the data from the DataTransferModel and prepares the data for the output
        (Creates a OutputDataModel for the use in Function `send_outputs()`).

        Args:
            data_output (DataTransferModel): DataTransferModel with the output data
            from the calculation

        Returns:
            OutputDataModel: OutputDataModel with the output data as formatted data
        """
        output_data = OutputDataModel(entities=[])

        if data_output is None:
            logger.debug("No data for preparing the output.")
            return output_data
        output_attrs: dict[str, list] = {}
        output_cmds: dict[str, list] = {}

        if self.config is None:
            logger.error(
                "Configuration is not loaded. Please call prepare_start() first."
            )
            return output_data

        for component in data_output.components:
            for output in self.config.outputs:
                if output.id == component.entity_id:
                    self._process_attributes(component, output, output_attrs)
                    self._process_commands(component, output, output_cmds)

        for output in self.config.outputs:
            attributes = output_attrs.get(output.id, [])
            commands = output_cmds.get(output.id, [])
            output_data.entities.append(
                OutputDataEntityModel(
                    id=output.id, attributes=attributes, commands=commands
                )
            )

        return output_data

    def _process_attributes(
        self,
        component: DataTransferComponentModel,
        output: OutputModel,
        output_attrs: dict,
    ) -> dict:
        """Helper function to process attributes."""
        for attribute in output.attributes:
            if attribute.id == component.attribute_id:
                if output.id not in output_attrs:
                    output_attrs[output.id] = []

                attribute.value = (
                    component.value if component.value is not None else attribute.value
                )

                output_attrs[output.id].append(
                    AttributeModel(
                        id=attribute.id,
                        value=attribute.value,
                        unit=component.unit,
                        timestamp=component.timestamp,
                    )
                )
                break
        return output_attrs

    def _process_commands(
        self,
        component: DataTransferComponentModel,
        output: OutputModel,
        output_cmds: dict,
    ) -> dict:
        """Helper function to process commands."""
        for command in output.commands:
            if command.id == component.attribute_id:
                if output.id not in output_cmds:
                    output_cmds[output.id] = []

                # TODO: type checking necessary? Dataframes and bools not allowed for commands
                command.value = (
                    component.value if component.value is not None else command.value
                )

                output_cmds[output.id].append(
                    CommandModel(id=command.id, value=command.value)
                )
                break
        return output_cmds

    def cleanup_service(self):
        """
        Cleanup the service resources:
            - MQTT Client
        If more resources are added in the future, make sure to clean them up here.
        """

        self.stop_mqtt_client()
        logger.debug("Service stopped, cleanup finished.")

    async def start_service(self):
        """
        Main function for converting the data
        """

        sampling_time = (
            self.config.controller_settings.time_settings.calculation.sampling_time
            * get_time_unit_seconds(
                self.config.controller_settings.time_settings.calculation.sampling_time_unit
            )
        )

        logger.info("Start the Service")
        # Hold the service for a time at the beginning,
        await self._hold_sampling_time(
            start_time=datetime.now(),
            hold_time=self.env.start_hold_time,
        )

        while not self.shutdown_event.is_set():
            logger.debug("Start the Prozess")
            start_time = datetime.now()

            if self.config.interfaces.fiware:
                self.update_authentication()

            data_input = await self.get_data(method=DataQueryTypes.CALCULATION)

            if data_input is not None:
                data_output = await self.calculation(data=data_input)

                data_output = self.prepare_output(data_output=data_output)

                await self.send_outputs(data_output=data_output)

            await self._set_health_timestamp()

            await self._hold_sampling_time(
                start_time=start_time, hold_time=sampling_time
            )

        logger.debug("Service will be stopped, running cleanup")
        self.cleanup_service()

    async def start_calibration(self):
        """
        Function for autonomous adjustment of the system parameters
        """

        if self.config.controller_settings.time_settings.calibration is None:
            logger.info(
                "No Information about the calibration time in the configuration. "
                "Calibration will not be performed."
            )
            return

        sampling_time = (
            self.config.controller_settings.time_settings.calibration.sampling_time
            * get_time_unit_seconds(
                self.config.controller_settings.time_settings.calibration.sampling_time_unit
            )
        )
        await self._hold_sampling_time(
            start_time=datetime.now(),
            hold_time=self.env.start_hold_time,
        )

        while not self.shutdown_event.is_set():
            logger.debug("Start Calibration")
            start_time = datetime.now()
            data_input = await self.get_data(method=DataQueryTypes.CALIBRATION)
            await self.calibration(data=data_input)

            await self._hold_sampling_time(
                start_time=start_time, hold_time=sampling_time
            )
        logger.debug("Calibration was stopped")

    async def check_health_status(self):
        """
        Function to check the health-status of the service
        """
        logger.debug("Start the Health-Check")
        while not self.shutdown_event.is_set():
            start_time = datetime.now()
            sampling_time = (
                self.config.controller_settings.time_settings.calculation.sampling_time
                * get_time_unit_seconds(
                    self.config.controller_settings.time_settings.calculation.sampling_time_unit
                )
            )

            await update_health_file(
                time_cycle=sampling_time,
                timestamp_health=self.timestamp_health,
                timestamp_now=start_time,
            )

            await self._hold_sampling_time(start_time=start_time, hold_time=10)

    async def _set_health_timestamp(self):
        """
        Function to set the timestamp of the last health-check
        """
        self.timestamp_health = datetime.now()
        return
