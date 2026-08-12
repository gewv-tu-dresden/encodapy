Internal Models
===============

Internal models for basic services are used to communicate between different components of the basic service and its components.

Data Handling Models
---------------------
These models are used for handling data within the basic service or its components.

.. automodule:: encodapy.utils.models
   :members:
   :undoc-members:
   :exclude-members: model_fields, model_config, model_computed_fields, model_extra, MetaDataModel, FiwareDatapointParameter, FiwareAuth, FiwareParameter, DatabaseParameter, FiwareConnectionParameter

Interface Communication Models
-------------------------------

These models are used for communication between the basic service and the interfaces.

.. autopydantic_model:: encodapy.utils.models.MetaDataModel
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

.. autopydantic_model:: encodapy.utils.models.FiwareDatapointParameter
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

.. autopydantic_model:: encodapy.utils.models.FiwareAuth
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

.. autopydantic_model:: encodapy.utils.models.FiwareParameter
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

.. autopydantic_model:: encodapy.utils.models.DatabaseParameter
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False

.. autopydantic_model:: encodapy.utils.models.FiwareConnectionParameter
   :model-show-config-summary: False
   :field-list-validators: False
   :model-show-field-summary: False
   :model-show-validator-members: False
   :model-show-validator-summary: False