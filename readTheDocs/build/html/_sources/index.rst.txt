.. Xbee-Gateway documentation master file, created by
   sphinx-quickstart on Mon May  5 16:09:20 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. Xbee-Gateway documentation
.. ==========================

.. Add your content using ``reStructuredText`` syntax. See the
.. `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
.. documentation for details.


.. .. toctree::
..    :maxdepth: 2
..    :caption: Contents:

XBee Gateway's documentation!
=============================

The **XBee Gateway** is a robust, Python-based industrial communication bridge designed for collecting, processing, and transmitting field data from distributed wireless RTUs (Remote Terminal Units) over Modbus TCP. Ideal for applications in oilfields, power plants, and SCADA-driven environments, it offers high reliability, scalability, and real-time data integration.

Project Features
----------------

- 📡 **XBee Radio Integration**: Acquires sensor and control data from remote RTUs using Digi XBee radios over serial communication.
- 🧠 **Data Parsing & Mapping**: Transforms binary payloads into human-readable formats or Modbus-compatible values through customizable logic.
- 🗃️ **Modbus TCP Server**: Maps parsed data to Modbus holding registers, enabling seamless integration with HMIs, PLCs, and SCADA systems.
- 🧩 **MongoDB Support**: Optionally logs historical or configuration data to a local or remote MongoDB database.
- 🧪 **Modular Architecture**: Designed with clear modular separation (polling, parsing, storage, Modbus context) for easy maintenance and extension.
- 🐍 **Python 3.9+ Compatible**: Optimized for low-resource embedded systems like the Raspberry Pi 4 (ARM64).

Use Cases
---------

- Oil & gas well monitoring
- Power plant instrumentation
- Remote industrial sensor aggregation
- SCADA gateway development

source code: https://github.com/n1lby73/xbeeGateway 

.. Documentation Contents
.. ----------------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   pages/installation
   pages/usage
   pages/modules
..    usage
..    configuration
..    api
..    development
..    troubleshooting
..    contributing

.. Indices and Tables
.. ------------------

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

