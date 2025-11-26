"""
Description: Module for handling calibration files for components.
This module provides functionality to read and write calibration data.
Authors: Martin Altenburger
"""
#TODO: do we want to keep both json and sqlite implementations?

import json
import tempfile
import os
from pathlib import Path
from loguru import logger

def get_file_path(path:str,
                  file_extension: str = ".json") -> Path:
    """
    Ensures the file path has the correct file extension.
    Args:
        path (str): The original file path.
        file_extension (str): The desired file extension (default is ".json").
    Returns:
        Path: The file path with the correct file extension.
    """
    return Path(path).with_suffix(file_extension)

def save_calibration_json(path: str, data: dict):
    """Saves calibration data to a JSON file atomically.
    Args:
        path (str): The file path where the calibration data should be saved.
        data (dict): The calibration data to be saved.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=get_file_path(path).parent
        ) as tmp:
            json.dump(data, tmp, indent=2, default=str)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, get_file_path(path))
    except (FileNotFoundError, FileExistsError) as e:
        logger.error(f"Failed to save calibration data: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def load_extrema_json(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)
