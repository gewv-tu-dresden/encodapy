"""
Description: This script creates a YAML file containing the JSON schema of the ConfigModel class.
Author: Martin Altenburger
"""

import yaml

from encodapy.config.models import ConfigModel

# Schema als JSON abrufen
schema = ConfigModel.model_json_schema()

# JSON nach YAML konvertieren
yaml_schema = yaml.dump(
    schema, sort_keys=False, allow_unicode=True, default_flow_style=False
)

# In Datei speichern
with open("schema.yml", "w", encoding="utf-8") as f:
    f.write(yaml_schema)
