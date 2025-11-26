"""
Description: Module for handling calibration data of components.
This module provides functionality to read and write calibration data.
Authors: Martin Altenburger
"""
from typing import Optional
from pathlib import Path
import sqlite3
from encodapy.components.thermal_storage.thermal_storage_config import TemperatureExtrema

class CalibrationData:
    """
    Class for handling calibration data using SQLite.
    Args:
        db_path (str): Path to the SQLite database file.
    """

    def __init__(self, db_path):
        self.db_path = Path(db_path).with_suffix(".sqlite")
        self.init_db(self.db_path)

    def init_db(self,
                db_path:str):
        """
        Initializes the SQLite database and creates necessary tables.
        Args:
            db_path (str): Path to the SQLite database file.
        """
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_extrema (
                sensor_index INTEGER PRIMARY KEY,
                min_value REAL,
                max_value REAL,
                updated_at TEXT
            )""")
    def save_extrema_sqlite(self,
                            sensor_index: int,
                            extrema: TemperatureExtrema):
        """Saves temperature extrema to the SQLite database.
        Args:
            sensor_index (int): The index of the sensor.
            extrema (TemperatureExtrema): The temperature extrema data to be saved.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """ INSERT INTO sensor_extrema(sensor_index,min_value,max_value,updated_at)
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
            print(f"An error occurred while saving extrema: {e}")

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
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute(
                    """SELECT min_value,max_value,updated_at 
                    FROM sensor_extrema WHERE sensor_index=?""",
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
            print(f"An error occurred while saving extrema: {e}")
            return None
