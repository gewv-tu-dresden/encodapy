Basic Configuration
===================

BasicConfiguration Model
------------------------
The `ConfigModel` is used for the general configuration of the basic service in EnCoDaPy.

.. autopydantic_model:: encodapy.config.models.ConfigModel
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

Also you need to configure some general settings via environment variables as described in :doc:`../readme`. The following information is required for the basic service configuration:

.. autopydantic_settings:: encodapy.config.env_values.BasicEnvVariables

As described in :doc:`interfaces`, other environment variables are required for the configuration of specific interfaces.

Specific Sub Models for the Configuration
-----------------------------------------

The following models are used as sub-models within the `ConfigModel` for specific configuration sections.

.. automodule:: encodapy.config.models
   :members:
   :show-inheritance:
   :undoc-members:
   :exclude-members: ConfigModel, model_fields, model_config, model_computed_fields, model_extra, DataFile, DataFileEntity, DataFileAttribute


