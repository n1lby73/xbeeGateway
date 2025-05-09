Usage
=====

This project consists of two individual components that work hand-in-hand to achieve a common goal:
a configuration **GUI** and the main **Python script**.

.. note::

   It is **mandatory** to have MongoDB installed and running locally before starting the application.
   Without it, no configuration or historical data will be stored.

   Please refer to the official MongoDB documentation to set up MongoDB for your operating system:
   https://www.mongodb.com/docs/manual/installation/

Starting the GUI
----------------

To launch the graphical user interface for managing device configurations, run:

.. code-block:: bash

   python -m modules.configGui

This will open a window allowing you to view, add, update, or delete XBee device configurations
stored in the MongoDB database.

Starting the Gateway Script
---------------------------

To start the Modbus gateway application, which polls XBee devices, maps data to Modbus registers,
and serves the Modbus TCP server, run:

.. code-block:: bash

   python run.py

This script initializes the Modbus context, sets up XBee polling, handles real-time communication with
XBee radios, and exposes the data over a Modbus TCP server interface for client applications.

Project Flow Summary
--------------------

1. **Ensure MongoDB is running locally.**
2. **Use the GUI (`python -m modules.configGui`)** to configure connected XBee radios and Modbus address ranges.
3. **Start the main application (`python run.py`)** to begin polling data and exposing it via Modbus TCP.

