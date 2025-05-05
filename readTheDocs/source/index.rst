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

The **XBee Gateway** is an industrial-grade Python-based communication bridge designed to collect, process, and expose field data from distributed wireless RTUs (Remote Terminal Units) over Modbus TCP. It is particularly suited for oilfields, power plants, and other SCADA-style environments where reliability, scalability, and real-time data integration are critical.

Project Features
----------------

- 📡 **XBee Radio Integration**: Collects sensor and control data from remote RTUs via Digi XBee radios using serial communication.
- 🧠 **Data Parsing & Mapping**: Converts binary payloads into human-readable or Modbus-compatible values using custom logic.
- 🗃️ **Modbus TCP Server**: Maps incoming data to Modbus holding registers, enabling integration with HMIs, PLCs, and SCADA systems.
- 🧩 **MongoDB Support**: Optionally stores historical or configuration data in a local or remote MongoDB database.
- 🧪 **Modular Architecture**: Built using a clean separation of concerns (polling, parsing, database, Modbus context), making it easy to extend or debug.
- 🐍 **Python 3.9+ Compatible**: Works reliably on embedded systems like Raspberry Pi 4 (ARM64) with low resource usage.

Use Cases
---------

- Oil & gas well monitoring
- Power plant instrumentation
- Remote industrial sensor aggregation
- SCADA gateway development

source code: https://github.com/n1lby73/xbeeGateway 

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   pages/installation
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

