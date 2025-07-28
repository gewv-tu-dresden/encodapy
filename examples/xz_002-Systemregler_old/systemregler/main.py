"""Main file to start the SystemController.

Copyright 2023, TUD Dresden University of Technology,
Faculty of Power Engineering
Chair of Building Energy Systems and Heat Supply
Authors:    Maximilian Beyer <maximilian.beyer@tu-dresden.de>.
"""

import logging
import time
from pathlib import Path

from systemcontroller.base.sc import SystemController


def find_config_or_runit_file() -> Path:
    """Find the RunIt config file in the configuration_directory."""
    # path to confuguration_directory
    config_dir = Path(__file__).parent / "configuration_directory"

    # list of all RunIt.json-filenames (should (!) be only one)
    config_files = [
        file.name
        for file in config_dir.iterdir()
        # if controller_config or RunIt json-file is found, return the path
        if file.name.startswith(("controller_config", "RunIt"))
        and file.suffix == ".json"
    ]

    # check whether at least one file was found
    if len(config_files) == 0:
        msg = "Could not find any RunIt.json file in configuration_directory."
        raise FileNotFoundError(msg)

    file = config_dir / config_files[0]

    if len(config_files) > 1:
        msg = "Found multiple config and/or RunIt files. Use now: " + str(file)

    if file.name.startswith("RunIt"):
        msg = "Found only RunIt-file(s): Does not work with current version of SystemController. Please contact the author."
        raise FileNotFoundError(msg)

    # path to RunIt.json file, if there are multiple files, take the first one
    return config_dir / config_files[0]


if __name__ == "__main__":
    # find RunIt.json file
    config_path = find_config_or_runit_file()

    # # Erstelle Datei Zustand
    # PB_zustand = zustand_PK()

    # # Erstelle Datei Zündvorgäng
    # PB_zuendung = anzahl_zuendung()

    # PB_endzeit = endzeit_pb()

    # create and start SystemController
    # TODO Mosig: Sollten die Textdateien nicht benötigt werden, Startwerte für PB-Zustände hier entfernen
    sc = SystemController(config_path) 
    sc.start()

    # the one and only print statement
    print(
        "SystemController "
        + sc.name
        + " started, find more information in the controller.log file.",
    )

    # exit here while testing

    # keep the main thread alive and performant
    time_to_sleep = 0.25
    if sc.syncchecker:
        logging.debug("SyncChecker is active. SystemController is running.")
        while True:
            sc.run()
            time.sleep(time_to_sleep)

    else:
        logging.debug(
            "SyncChecker is not active, that case is not implemented yet. SystemController shut down.",
        )
