Usage
=====

There are two ways to run the XBee Gateway:

The development mode is intended for testing and debugging, while the production mode is designed for deployment on a Raspberry Pi or any systemd-based system. The following sections provide detailed instructions for both modes.

.. note::

    **Development** – Applicable on all operating systems.  
    
    **Production** – Only applicable on Linux systems that support systemd.  

    Make sure you are working in the directory where you cloned the repository.

    **Path** e.g., `/home/pi/xbeeGateway`.

1. Development Mode
-------------------

Starting the GUI
^^^^^^^^^^^^^^^^

To launch the graphical user interface for managing device configurations, run:

.. code-block:: bash

    python -m modules.configGui

This will open a window allowing you to view, add, update, or delete XBee device configurations stored in the MongoDB database.

Starting the Gateway Script
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start the Modbus gateway application, which polls XBee devices, maps data to Modbus registers, and serves the Modbus TCP server, run:

.. code-block:: bash

    python run.py

This script initializes the Modbus context, sets up XBee polling, handles real-time communication with XBee radios, and exposes the data over a Modbus TCP server interface for client applications.

Project Flow Summary
^^^^^^^^^^^^^^^^^^^^^

1. **Ensure MongoDB is running locally.**
2. **Use the GUI (`python -m modules.configGui`)** to configure connected XBee radios and Modbus address ranges.
3. **Start the main application (`python run.py`)** to begin polling data and exposing it via Modbus TCP.


2. Production Mode
------------------

This guide explains how to set up and manage two systemd services—xbeeGateway and xbeeGui—for the CORS Gateway on a Raspberry Pi or any systemd-based system. These services ensure the gateway and its GUI start automatically and run continuously, including after reboots.
Set up the systemd services as described below to run the gateway automatically on startup and ensure it restarts in case of failure. The project is composed of two components that work together to achieve a unified goal: a configuration GUI for managing device settings and the main Python script that handles Modbus communication.

Systemd Service Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section describes the configuration and usage of the **CORS Gateway** systemd services: ``xbeeGateway`` and ``xbeeGui``. These services ensure the gateway runs continuously on a Raspberry Pi (or other systemd-compatible system), handling initialization and recovery as needed.

1. Customize the Service Files
"""""""""""""""""""""""""""""""

Edit the following lines in both ``xbeeGateway.service`` and ``xbeeGui.service`` files:

.. code-block:: ini

    User={your username}
    WorkingDirectory={directory where you cloned the repository}

Replace the placeholders with your actual system username and the full path to the ``xbeeGateway`` directory.

2. Move Service Files to systemd Directory
"""""""""""""""""""""""""""""""""""""""""""
.. code-block:: bash

    sudo cp xbeeGateway.service /etc/systemd/system/
    sudo cp xbeeGui.service /etc/systemd/system/

3. Reload and Enable the Services
""""""""""""""""""""""""""""""""""

.. code-block:: bash

    sudo systemctl daemon-reload
    sudo systemctl enable xbeeGateway
    sudo systemctl enable xbeeGui

4. Start the Services
""""""""""""""""""""""

.. code-block:: bash

    sudo systemctl start xbeeGateway
    sudo systemctl start xbeeGui

5. Verify the Services
"""""""""""""""""""""""

Check if the services are running:

.. code-block:: bash

    sudo systemctl status xbeeGateway
    sudo systemctl status xbeeGui

The output for ``xbeeGateway`` should resemble:

.. code-block:: text

    xbeeGateway.service - CORS Gateway
         Loaded: loaded (/etc/systemd/system/xbeeGateway.service; enabled; preset: >)
         Active: active (running) since Thu 2025-05-22 13:52:05 BST; 2h 53min ago
        Process: 4494 ExecStartPre=/usr/bin/bash -c lsof -ti:5020 | xargs -r kill ->
        Process: 4497 ExecStartPre=/bin/sleep 2 (code=exited, status=0/SUCCESS)
       Main PID: 4499 (python)
          Tasks: 10 (limit: 3913)
            CPU: 1min 33.389s
         CGroup: /system.slice/xbeeGateway.service
                 └─4499 /home/pi/xbeeGateway/venv/bin/python /home/pi/xbeeGateway/run.py

    May 22 13:52:03 raspberrypi systemd[1]: Starting xbeeGateway.service - CORS Gateway...
    May 22 13:52:05 raspberrypi systemd[1]: Started xbeeGateway.service - CORS Gateway.

6. Log Verification
""""""""""""""""""""

Navigate to the project directory:

.. code-block:: bash

    cd /home/pi/xbeeGateway

Ensure the following files are created:

- ``corsGatewayService.txt`` – logs standard service output
- ``corsGatewayErrorService.txt`` – logs error messages

If both files are **empty**:

1. Confirm that your radio is connected and receiving data.
2. Fix file ownership if necessary:

.. code-block:: bash

    sudo chown pi:pi /home/pi/xbeeGateway/corsGatewayService.txt
    sudo chown pi:pi /home/pi/xbeeGateway/corsGatewayErrorService.txt

.. warning::

   If you encounter a "cannot bind" error, it likely means the gateway is already running—possibly in production mode—while you're trying to start it in development mode. 

   First, ensure no other instance is running. If needed, terminate any process using port 502 or 5020:

   .. code-block:: bash

      sudo kill -9 $(sudo lsof -t -i :5020)

   To list all processes using ports 502 or 5020:

   .. code-block:: bash

      lsof -t -i :5020
