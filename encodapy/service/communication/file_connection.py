"""
Description: This file contains the class FiwareConnections, 
which is used to store the connection parameters for the Fiware and CrateDB connections.
Author: Paul Seidel
"""

import os
import json
import pathlib
from datetime import datetime
from typing import Union
from loguru import logger
import pandas as pd
from encodapy.config import (
    AttributeModel,
    AttributeTypes,
    CommandModel,
    DataQueryTypes,
    DefaultEnvVariables,
    FileExtensionTypes,
    InputModel,
    OutputModel,
    StaticDataModel,
    StaticDataFile
)
from encodapy.utils.models import (
    InputDataAttributeModel,
    InputDataEntityModel,
    OutputDataEntityModel,
    StaticDataEntityModel,
)
from encodapy.utils.error_handling import NotSupportedError
from encodapy.utils.units import DataUnits


class FileConnection:
    """
    Class for the connection to a local file.
    Only a helper class.
    """

    def __init__(self):
        self.file_params = {}

    def load_file_params(self):
        """
        Function to load the file parameters
        """
        logger.debug("Load config for File interface")
        self.file_params["PATH_OF_INPUT_FILE"] = os.environ.get(
            "PATH_OF_INPUT_FILE", DefaultEnvVariables.PATH_OF_INPUT_FILE.value
        )
        self.file_params["START_TIME_FILE"] = os.environ.get(
            "START_TIME_FILE", DefaultEnvVariables.START_TIME_FILE.value
        )
        self.file_params["TIME_FORMAT_FILE"] = os.environ.get(
            "TIME_FORMAT_FILE", DefaultEnvVariables.TIME_FORMAT_FILE.value
        )
        self.file_params["PATH_OF_STATIC_DATA"] = os.environ.get(
            "PATH_OF_STATIC_DATA", DefaultEnvVariables.PATH_OF_STATIC_DATA.value
        )

    def _get_last_timestamp_for_file_output(
        self, output_entity: OutputModel
    ) -> tuple[OutputDataEntityModel, Union[datetime, None]]:
        """
        Function to get the latest timestamps of the output entity from a File, if exitst

        Args:
            output_entity (OutputModel): Output entity

        Returns:
            tuple[OutputDataEntityModel, Union[datetime, None]]:
                - OutputDataEntityModel with timestamps for the attributes
                - the latest timestamp of the output entity for the attribute
                with the oldest value (None if no timestamp is available)
        TODO:
            - is it really nessesary to get a timestamp for file-calculations /
            during calculation time is set to input_time
        """

        output_id = output_entity.id_interface

        timestamps = []
        timestamp_latest_output = None

        return (
            OutputDataEntityModel(id=output_id, attributes_status=timestamps),
            timestamp_latest_output
        )

    def get_data_from_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """f
        Function to check input data-file and load data, \
        check of the file extension (compare in lower cases)

        Args:
            method (DataQueryTypes): Keyword for type of query
            entity (InputModel): Input entity

        Raises:
            NotSupportedError: If the file extension is not supported

        Returns:
            Union[InputDataEntityModel, None]: Model with the input data or \
                None if no data is available
        """

        file_extension = pathlib.Path(self.file_params["PATH_OF_INPUT_FILE"]).suffix.lower()

        if file_extension == FileExtensionTypes.CSV.value:
            logger.info(f"load config for {file_extension} -file")
            data = self.get_data_from_csv_file(method=method, entity=entity)
        elif file_extension == FileExtensionTypes.JSON.value:
            logger.info(f"load config for {file_extension} -file")
            data = self.get_data_from_json_file(method=method, entity=entity)
        else:
            logger.info(f"File extension {file_extension} is not supported")
            raise NotSupportedError

        return data

    def get_data_from_csv_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """
            Function to read input data for calculations from a input file.
            first step: read the first values in the file / id_inputs.
            Then get the data from the entity since the last timestamp
            of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
             - timestamp_latest_output (datetime): Timestamp of the input value
             -  -> seperating Data in Calculation or here ??
             - handle the methods for the file interface

        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection
            to the platform is not available

        """
        # TODO: Implement method handling for file interface
        _ = method  # Acknowledge unused parameter

        # attributes_timeseries = {}
        attributes_values = []
        path_of_file = self.file_params["PATH_OF_INPUT_FILE"]
        time_format = self.file_params["TIME_FORMAT_FILE"]
        try:
            data = pd.read_csv(path_of_file, parse_dates=["Time"], sep=";", decimal=",")
            data.set_index("Time", inplace=True)
            data.index = pd.to_datetime(data.index, format=time_format)
            # time = self.file_params["START_TIME_FILE"]
            # temp = data.loc[time, 'outside_Temperature']
        except FileNotFoundError:
            logger.error(f"Error: File not found ({path_of_file})")
            # TODO: What to do if the file is not found?
            return None
        for attribute in entity.attributes:

            if attribute.type == AttributeTypes.TIMESERIES:
                # attributes_timeseries[attribute.id] = attribute.id_interface
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )
            elif attribute.type == AttributeTypes.VALUE:

                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=data[attribute.id_interface].iloc[0],
                        data_type=AttributeTypes.VALUE,
                        data_available=True,
                        latest_timestamp_input=data.index[0],
                    )
                )
            else:
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def get_data_from_json_file(
        self,
        method: DataQueryTypes,
        entity: InputModel,
    ) -> Union[InputDataEntityModel, None]:
        """
            Function to read input data for calculations from a input file.
            first step: read the keys and values in the file / id_inputs.
            Then get the data from the entity since the last timestamp
            of the output entity from cratedb.
        Args:
            - method (DataQueryTypes): Keyword for type of query
            - entity (InputModel): Input entity
        TODO:
             - timestamp_latest_output (datetime): Timestamp of the input value
             -  -> seperating Data in Calculation or here ??
             - handle the methods for the file interface

        Returns:
            - InputDataEntityModel: Model with the input data or None if the connection
            to the platform is not available

        """
        # TODO: Implement method handling for file interface
        _ = method  # Acknowledge unused parameter

        # attributes_timeseries = {}
        attributes_values = []
        path_of_file = self.file_params["PATH_OF_INPUT_FILE"]
        time_format = self.file_params["TIME_FORMAT_FILE"]
        try:
            #read data from json file and timestamp
            with open(path_of_file, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Error: File not found ({path_of_file})")
            # TODO: What to do if the file is not found?
            return None
        for attribute in entity.attributes:
            if attribute.type == AttributeTypes.TIMESERIES:
                # attributes_timeseries[attribute.id] = attribute.id_interface

                for input_data in data:
                    time = datetime.strptime(input_data['time'], time_format)
                    if attribute.id_interface == input_data['id_interface']:
                        attributes_values.append(
                            InputDataAttributeModel(
                                id=attribute.id,
                                data=input_data['value'],
                                data_type=AttributeTypes.TIMESERIES,
                                data_available=True,
                                latest_timestamp_input=time,
                            )
                        )
            elif attribute.type == AttributeTypes.VALUE:

                attributes_values.append(
                    InputDataAttributeModel(
                        id=attribute.id,
                        data=data[attribute.id_interface].iloc[0],
                        data_type=AttributeTypes.VALUE,
                        data_available=True,
                        latest_timestamp_input=data.index[0],
                    )
                )
            else:
                logger.warning(
                    f"Attribute type {attribute.type} for attribute {attribute.id}"
                    f"of entity {entity.id} not supported."
                )

        return InputDataEntityModel(id=entity.id, attributes=attributes_values)

    def _get_unit_from_file(
        self,
        metadata: Union[dict[str, str], None],
    ) -> Union[DataUnits, None]:
        """
        Extracts the unit from the metadata dictionary.
        
        Args:
            metadata (Union[dict[str, str], None]): Metadata dictionary or None.
        Returns:
            Union[DataUnits, None]: Extracted data unit or None.
        """

        if metadata is None:
            return None
        if not isinstance(metadata, dict):
            logger.warning(
                f"Metadata is not a dictionary: {metadata}"
            )
            return None
        metadata_lowercase = {
            k.lower(): v for k, v in metadata.items()
        }
        unit = metadata_lowercase.get("unitcode", None)
        if unit:
            return DataUnits(unit)
        return None

    def get_staticdata_from_file(
        self,
        entity: StaticDataModel,
    ) -> Union[StaticDataEntityModel, None]:
        """
        Function to read static data for calculations from config file.
        Args:
            - entity (StaticDataModel): Input entity
        TODO:
            - work with timeseries, for example: timetable with presence or heating_times

        Returns:
            - StaticDataEntityModel: Model with the static data

        """

        static_data_path = self.file_params["PATH_OF_STATIC_DATA"]

        attributes_values = []

        try:
            #read data from json file and timestamp
            with open(static_data_path, encoding="utf-8") as f:
                static_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Error: File not found ({static_data_path})")
            # TODO: What to do if the file is not found?
            return None
        if isinstance(static_data, list):
            static_data = {"staticdata": static_data}
        elif isinstance(static_data, dict):
            pass
        else:
            logger.error(f"Error: Unsupported data format ({static_data_path})")
            return None

        static_data = StaticDataFile.model_validate(static_data)

        for attribute in entity.attributes:

            for item_entity in static_data.staticdata:
                for item_attribute in item_entity.attributes:
                    if item_attribute.id == attribute.id:

                        attributes_values.append(
                                InputDataAttributeModel(
                                    id=attribute.id,
                                    data=item_attribute.value,
                                    unit=self._get_unit_from_file(item_attribute.metadata),
                                    data_type=AttributeTypes.VALUE,
                                    data_available=True,
                                    latest_timestamp_input=None,
                                    )
                                )

        return StaticDataEntityModel(id=entity.id, attributes=attributes_values)


    def send_data_to_json_file(
        self,
        output_entity: OutputModel,
        output_attributes: list[AttributeModel],
        output_commands: list[CommandModel],
    ) -> None:
        """_Function to create a json_file in result-folder

        Args:
            output_entity (OutputModel): _description_
            output_attributes (list[AttributeModel]): _description_
            output_commands (list[CommandModel]): _description_

        Out: Json-file

        TODO:
            - Is it better to set the results-folder via env?
        """
        outputs = []
        commands = []
        logger.debug("Write outputs to json-output-files")

        if not os.path.exists("./results"):
            os.makedirs("./results")

        for output in output_attributes:
            outputs.append(
                {
                    "id_interface": output.id_interface,
                    "value": output.value,
                    "time": output.timestamp.strftime("%H:%M:%S %d.%m.%Y"),
                }
            )

        with open(f"./results/outputs_{str(output_entity.id)}.json",
                  "w", encoding="utf-8") as outputfile:
            json.dump(outputs, outputfile)

        for command in output_commands:
            commands.append(
                {
                    "id_interface": command.id_interface,
                    "value": command.value,
                    "time": command.timestamp.strftime("%H:%M:%S %d.%m.%Y"),
                }
            )

        with open("./results/commands.json", "w", encoding="utf-8") as commandfile:
            json.dump(commands, commandfile)
