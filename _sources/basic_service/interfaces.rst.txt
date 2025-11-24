Communication Interfaces
=========================

Configuration of the FIWARE Interface
-------------------------------------
The FIWARE Interface allows communication with FIWARE-based systems using the NGSI standard.
For details about the Usage of FIWARE see `N5GEH <https://github.com/N5GEH/n5geh.tutorials.from_sensor_to_application>`_
or the FIWARE `openapi documentation <https://github.com/FIWARE/specifications>`_.
Until now, only NGSI v2 is supported.

You need to configure some general settings via environment variables. The following information is required for the FIWARE interface configuration:

.. autopydantic_settings:: encodapy.config.env_values.FiwareEnvVariables


Configuration of the MQTT Interface
------------------------------------
The MQTT Interface allows communication with MQTT brokers for publishing and subscribing to topics.
You need to configure some general settings via environment variables. The following information is required for the MQTT interface configuration:

.. autopydantic_settings:: encodapy.config.env_values.MQTTEnvVariables

You could use different topics and payload templates for publishing and subscribing to MQTT messages.

- For possible kinds of mqtt message formats, see :class:`~encodapy.config.types.MQTTFormatTypes`.
- You need to configure the usage in the :class:`~encodapy.config.models.AttributeModel`.

For a custom template, the following model is used:

.. autopydantic_model:: encodapy.config.mqtt_messages_template.MQTTTemplateConfig
    :exclude-members: model_json_schema
    :model-show-json: False


Configuration of the File Interface
------------------------------------

The File Interface allows reading from and writing to data files.
You need also to configure some general settings via environment variables. The following information is required for the file interface configuration:

.. autopydantic_settings:: encodapy.config.env_values.FileEnvVariables

For the specific configuration / structure of used data files, the following models are used:

.. autopydantic_model:: encodapy.config.models.DataFile


.. autopydantic_model:: encodapy.config.models.DataFileEntity


.. autopydantic_model:: encodapy.config.models.DataFileAttribute
