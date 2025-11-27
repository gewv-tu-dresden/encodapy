"""
Description: Module for handling calibration data of components.
This module provides functionality to read and write calibration data.
Authors: Martin Altenburger
"""
from typing import Optional
from pathlib import Path
import sqlite3
from datetime import datetime
from loguru import logger
from encodapy.components.thermal_storage.thermal_storage_config import (
    TemperatureExtrema,
    ThermalStorageTemperatureSensors
    )

class CalibrationData:
    """
    Class for handling calibration data using SQLite.
    Args:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, db_path)-> None:
        self.db_path = Path(db_path).with_suffix(".sqlite")
        self.tables: list[str] = ["sensor_extrema", "sensor_limits"]
        self.init_db(self.db_path)

    def init_db(self,
                db_path:Path):
        """
        Initializes the SQLite database and creates necessary tables.
        Args:
            db_path (Path): Path to the SQLite database file.
        """
        for table in self.tables:
            with sqlite3.connect(db_path) as conn:
                conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    sensor_index INTEGER PRIMARY KEY,
                    min_value REAL,
                    max_value REAL,
                    updated_at TEXT
                )""")
    def _save_values_sqlite(self,
                           sensor_index: int,
                           table: str,
                           extrema: TemperatureExtrema
                           )-> None:
        """Saves temperature extrema to the specified SQLite table.
        Args:
            sensor_index (int): The index of the sensor.
            table (str): The name of the table to save the data to.
            extrema (TemperatureExtrema): The temperature extrema data to be saved.
        """
        if table not in self.tables:
            logger.error(f"Table {table} is not recognized.")
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f""" INSERT INTO {table}(sensor_index,min_value,max_value,updated_at)
                    VALUES(?,?,?,?)
                    ON CONFLICT(sensor_index) DO UPDATE SET
                        min_value=excluded.min_value,
                        max_value=excluded.max_value,
                        updated_at=excluded.updated_at
                    """, (
                    sensor_index,
                    extrema.minimal_temperature,
                    extrema.maximal_temperature,
                    extrema.time.isoformat())
                )
        except sqlite3.Error as e:
            logger.error(f"An error occurred while saving extrema: {e}")

    def save_extrema_sqlite(self,
                            sensor_index: int,
                            extrema: TemperatureExtrema
                            )-> None:
        """Saves temperature extrema to the SQLite database.
        Args:
            sensor_index (int): The index of the sensor.
            extrema (TemperatureExtrema): The temperature extrema data to be saved.
        """
        return self._save_values_sqlite(
            sensor_index = sensor_index,
            table = "sensor_extrema",
            extrema = extrema
        )

    def save_limits_sqlite(self,
                           sensor_config: ThermalStorageTemperatureSensors,
                           )-> None:
        """Saves temperature limits to the SQLite database.
        Args:
            sensor_index (int): The index of the sensor.
            extrema (TemperatureExtrema): The temperature limits data to be saved.
        """
        for sensor_index, sensor in enumerate(
            sensor_config.storage_sensors
            ):
            extrema = TemperatureExtrema(
                minimal_temperature=sensor.limits.minimal_temperature,
                maximal_temperature=sensor.limits.maximal_temperature,
                time=datetime.utcnow()
            )
            self._save_values_sqlite(
                sensor_index = sensor_index,
                table = "sensor_limits",
                extrema = extrema
            )

    def load_values_sqlite(self,
                           sensor_index:int,
                            table:str
                            )-> Optional[TemperatureExtrema]:
        """Loads temperature extrema from the specified SQLite table.
        Args:
            sensor_index (int): The index of the sensor.
            table (str): The name of the table to load the data from.
        Returns:
            Optional[TemperatureExtrema]: The loaded temperature extrema data,\
                or None if not found.
        """
        if table not in self.tables:
            logger.error(f"Table {table} is not recognized.")
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    f"""SELECT min_value,max_value,updated_at 
                    FROM {table} WHERE sensor_index=?""",
                    (sensor_index,)
                    )
                row = cur.fetchone()
                if row is None:
                    return None
                extrema = TemperatureExtrema(
                    minimal_temperature=row[0],
                    maximal_temperature=row[1],
                    time=row[2]
                )
                return extrema
        except sqlite3.Error as e:
            logger.error(f"An error occurred while saving extrema: {e}")
            return None

    def load_extrema_sqlite(self,
                            sensor_index:int
                            )-> Optional[TemperatureExtrema]:
        """Loads temperature extrema from the SQLite database.
        Args:
            sensor_index (int): The index of the sensor.
        Returns:
            Optional[TemperatureExtrema]: The loaded temperature extrema data,\
                or None if not found.
        """
        return self.load_values_sqlite(
            sensor_index = sensor_index,
            table = "sensor_extrema"
        )

    def load_limits_sqlite(self,
                           sensor_config: ThermalStorageTemperatureSensors
                           )-> ThermalStorageTemperatureSensors:
        """
        Loads temperature limits from the SQLite database and updates the sensor configuration.

        Args:
            sensor_config (ThermalStorageTemperatureSensors): \
                The sensor configuration to be updated.

        Returns:
            ThermalStorageTemperatureSensors: The updated sensor configuration.
        """
        for sensor_index, sensor in enumerate(
            sensor_config.storage_sensors
            ):
            extrema = self.load_values_sqlite(
                sensor_index = sensor_index,
                table = "sensor_limits"
            )
            if extrema is not None:
                sensor.limits.minimal_temperature = extrema.minimal_temperature
                sensor.limits.maximal_temperature = extrema.maximal_temperature

        return sensor_config
