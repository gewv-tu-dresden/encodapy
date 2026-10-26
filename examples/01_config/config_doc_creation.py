"""
Description: This script creates a YAML file containing the JSON schema of the ConfigModel class.
Author: Martin Altenburger
"""

import yaml

from encodapy.config.models import ConfigModel

# Get schema of ConfigModel
schema = ConfigModel.model_json_schema()

# Convert JSON to YAML
yaml_schema = yaml.dump(
    schema, sort_keys=False, allow_unicode=True, default_flow_style=False
)

# Write YAML schema to file
with open("schema.yml", "w", encoding="utf-8") as f:
    f.write(yaml_schema)
