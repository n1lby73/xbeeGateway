Modules
============

.. _main:

main
----

The `main` module is the entry point of the XBee Gateway application. It orchestrates the XBee serial communication, Modbus TCP server, and processing of sensor data from XBee radios. It uses `asyncio` to handle concurrent tasks efficiently.

Module Setup
^^^^^^^^^^^^

Imports
"""""""

The following standard and third-party modules are imported:

- ``sys``, ``asyncio``, ``datetime``: Core Python modules for system interaction, concurrency, and time.
- ``digi.xbee.devices.XBeeDevice`` and ``digi.xbee.exception.XBeeException``: For managing XBee communication and handling related exceptions.
- ``pymodbus.server.StartAsyncTcpServer`` and ``pymodbus.device.ModbusDeviceIdentification``: Used to run and identify the Modbus TCP server.
- Application-specific modules:
  
  - ``modules.variables``: Stores shared runtime variables such as XBee instance, known MACs, Modbus port, etc.
  - ``modules.xbeeData.cayenneParse``: Parses incoming XBee payloads into float values using Cayenne LPP protocol.
  - ``modules.dbIntegration.dbQueryModbusStartAddress``: Maps MAC addresses to Modbus register start addresses.
  - ``modules.serialSelector``: Contains:
    - ``selectUsbPort``: Chooses an available USB port.
    - ``handleUsbDisconnection``: (commented out) handles disconnection events.
  - ``modules.modbus``: Provides:
    - ``floatToRegisters``: Converts float values to 2 x 16-bit Modbus register pairs.
    - ``contextManager``: Returns a Modbus context for register mapping.
    - ``getIpAddress``: Determines local IP address for Modbus server binding.

XBee Device Initialization
"""""""""""""""""""""""""""

XBee Serial Port Selection
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    serialPort = selectUsbPort()

- Attempts to detect which USB port the XBee radio is connected to.
- If successful, the returned serial port is used to instantiate an `XBeeDevice`.

Creating the XBeeDevice
"""""""""""""""""""""""

.. code-block:: python

    variables.xbeeInstance = XBeeDevice(serialPort, variables.xbeeBaudRate)

- A global reference to the `XBeeDevice` is stored in `variables.xbeeInstance`.
- The baud rate is fetched from shared config `variables.xbeeBaudRate`.

Fallback if Device Not Found
"""""""""""""""""""""""""""""

.. code-block:: python

    if not serialPort:
        print("Gateway radio not connected")
        sys.exit(1)

- If no serial port is returned (e.g., no USB radio plugged in), the system exits early with an error message.

Queue Initialization
"""""""""""""""""""""

.. code-block:: python

    xbeeQueue = asyncio.Queue()

- Initializes an asynchronous queue.
- Each entry in the queue is a tuple: ``(mac_address, raw_data_bytes)``.
- This queue decouples the reception of XBee packets from the Modbus writing process.

``xbeeQueue`` is consumed by `modbusPolling()` and populated by `xbeePolling()`.

``variables.xbeeInstance`` is a global variable, required across the entire script to maintain a reference to the XBee radio device for receiving messages and handling connections.

Summary
"""""""""

This initialization block ensures that:

- All required modules and helpers are available.
- The XBee radio is located and configured for communication.
- A global queue is prepared for non-blocking data processing.
- The application halts gracefully if the XBee device is not connected.

``main`` is not just an entry point — it’s the coordination layer that glues asynchronous XBee communication, database-driven register mapping, and Modbus server exposure into a coherent, reactive gateway service.

xbeePolling
^^^^^^^^^^^

The `xbeePolling` coroutine handles continuous communication with the connected XBee radio. It listens for incoming RF messages and queues them for further processing by the Modbus layer.

Overview
"""""""""

This function:

- Opens the serial port and establishes a connection with the XBee device.
- Registers a callback to process incoming data asynchronously.
- Extracts metadata like the MAC address, timestamp, and payload.
- Adds any newly discovered MAC addresses to a global known list.
- Pushes each received packet into the global `xbeeQueue`.

Implementation
"""""""""""""""

.. code-block:: python

    async def xbeePolling():
        try:
            variables.xbeeInstance.open()

            def dataReceiveCallback(xbeeMessage):
                ...

            variables.xbeeInstance.add_data_received_callback(dataReceiveCallback)

            while True:
                await asyncio.sleep(1)
        except Exception as e:
            print(e)
        finally:
            if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():
                variables.xbeeInstance.close()

Data Reception Callback
"""""""""""""""""""""""

.. code-block:: python

    def dataReceiveCallback(xbeeMessage):
        xbeeMacAddress = str(xbeeMessage.remote_device.get_64bit_addr())
        timestamp = datetime.fromtimestamp(xbeeMessage.timestamp)
        xbeeDataAsByte = xbeeMessage.data

This callback extracts:

- **xbeeMacAddress**: The 64-bit MAC address of the sending node.
- **timestamp**: Human-readable time of reception.
- **xbeeDataAsByte**: Raw binary payload sent by the remote device.

New Address Detection
"""""""""""""""""""""

.. code-block:: python

    if str(xbeeMacAddress) not in variables.knownXbeeAddress:
        print(f"\nNew XBee Address Discovered: {xbeeMacAddress}")
        variables.knownXbeeAddress.append(str(xbeeMacAddress))
        print(f"List of addresses discovered so far are: {variables.knownXbeeAddress}\n")

This section dynamically maintains a list of all MAC addresses seen during runtime. Newly discovered radios are appended to `variables.knownXbeeAddress`.

Queueing the Packet
"""""""""""""""""""""

.. code-block:: python

    xbeeQueue.put_nowait((xbeeMacAddress, xbeeDataAsByte))

- The `(mac, data)` tuple is inserted into the asynchronous `xbeeQueue`.
- This decouples reception from processing, allowing later stages to consume data without blocking.

Notes
"""""""

- The inner `while True` loop is necessary to keep the `xbeePolling` coroutine alive.
- `asyncio.sleep(1)` is a lightweight way to yield control while keeping the task running.
- If any exceptions occur, the serial port is closed in the `finally` block to avoid lockups.

Commented-Out Disconnection Handler
"""""""""""""""""""""""""""""""""""

There is a placeholder for future support of USB disconnection events:

.. code-block:: python

    # variables.xbeeInstance.add_error_callback(partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance))

This uses a `functools.partial` to prebind the device instance and register a disconnection handler, but it is currently disabled (commented out).

Summary
"""""""""

The `xbeePolling` function acts as the real-time listener for incoming XBee packets. It enables:

- Automatic discovery of new radios.
- Timestamped payload extraction.
- Non-blocking handoff to downstream Modbus and database processes via a shared queue.

modbusPolling
^^^^^^^^^^^^^^

The `modbusPolling` coroutine processes packets received from XBee radios and updates the Modbus server with the parsed sensor data.

Overview
"""""""""

This function:

- Waits for new entries from the shared `xbeeQueue`.
- Uses the MAC address to query a database and retrieve the Modbus register start address.
- Parses raw binary payloads into floating-point sensor values using the Cayenne LPP format.
- Converts floats into Modbus register values (16-bit integers).
- Writes up to 20 registers to both the Holding (FC3) and Input (FC4) register blocks.

Implementation
"""""""""""""""

.. code-block:: python

    async def modbusPolling(contextValue):
        while True:
            mac, raw_data = await xbeeQueue.get()
            try:
                startAddress = dbQueryModbusStartAddress(mac)
                if isinstance(startAddress, int):
                    sensorValues = await cayenneParse(mac, raw_data)
                    registerValues = []
                    for val in sensorValues:
                        registerValues.extend(floatToRegisters(val))
                    registers = registerValues[:20]
                    contextValue[0].setValues(3, startAddress, registers)
                    contextValue[0].setValues(4, startAddress, registers)
                else:
                    print(f"Xbee radio with mac address {mac}, has not been configured\nOther possible error are {startAddress}")
            except Exception as e:
                print(f"Modbus polling error: {str(e)}")
            finally:
                xbeeQueue.task_done()
                await asyncio.sleep(0)

Queue Consumption
"""""""""""""""""""

.. code-block:: python

    mac, raw_data = await xbeeQueue.get()

The coroutine waits (asynchronously) for new packets inserted by `xbeePolling()`. Each packet contains:

- `mac`: 64-bit MAC address as a string.
- `raw_data`: binary payload received from the XBee node.

Register Lookup
"""""""""""""""

.. code-block:: python

    startAddress = dbQueryModbusStartAddress(mac)

This line queries the local database to determine where in the Modbus address space the data from this MAC should be written. The database should return a valid starting address (e.g., 4020), or an error object if the address is unregistered.

Payload Parsing
"""""""""""""""""

.. code-block:: python

    sensorValues = await cayenneParse(mac, raw_data)

This function decodes the Cayenne Low Power Payload (LPP) format into a list of float values representing sensor readings. It is assumed to be robust to errors in payload structure.

Float to Register Conversion
"""""""""""""""""""""""""""""

.. code-block:: python

    registerValues = []
    for val in sensorValues:
        registerValues.extend(floatToRegisters(val))

Each float is converted into two 16-bit integers (Modbus registers) using IEEE 754 binary representation. Only the first 10 floats (20 registers) are used to ensure compatibility and prevent overflow:

.. code-block:: python

    registers = registerValues[:20]

Writing to Modbus Context
"""""""""""""""""""""""""

.. code-block:: python

    contextValue[0].setValues(3, startAddress, registers)
    contextValue[0].setValues(4, startAddress, registers)

This writes the register block to both:

- Function Code 3 (Holding Registers)
- Function Code 4 (Input Registers)

Both address spaces mirror the same sensor values, allowing flexibility for downstream SCADA or HMI systems.

Error Handling
"""""""""""""""

- If the MAC is not found in the database, a message is printed.
- Any exception during parsing or writing is caught and printed.
- After processing (even in error cases), `xbeeQueue.task_done()` is called to mark the queue task as complete.

Summary
"""""""

The `modbusPolling` function acts as the transformation and mapping layer of the gateway. It:

- Decouples data reception from register updates.
- Leverages asynchronous concurrency to handle large volumes of packets.
- Ensures safe and consistent updates to the Modbus context.

modbusServer
^^^^^^^^^^^^^

The `modbusServer` coroutine starts the asynchronous Modbus TCP server that exposes sensor data to external SCADA or HMI systems.

Overview
""""""""""

This function:

- Initializes the Modbus device identification parameters.
- Retrieves the local IP address dynamically.
- Launches the `StartAsyncTcpServer()` from `pymodbus` to serve the register context.
- Runs as an asyncio task concurrently with XBee polling and Modbus data processing.

Implementation
"""""""""""""""

.. code-block:: python

    async def modbusServer(context):
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'Cors System'
        identity.ProductCode = 'CSG'
        identity.VendorUrl = 'https://corssystem.com'
        identity.ProductName = 'Core Terminal Unit Gateway'
        identity.ModelName = 'Genesis'
        identity.MajorMinorRevision = '2.0'

        ipAddress = getIpAddress()
        print(f"Starting Modbus TCP server on port {variables.modbusPort}...")
        await StartAsyncTcpServer(context, identity=identity, address=(ipAddress, variables.modbusPort))

Modbus Identity Configuration
"""""""""""""""""""""""""""""

The identity block provides descriptive information about the gateway device when queried by Modbus clients:

.. code-block:: text

    VendorName           = Cors System
    ProductCode          = CSG
    ProductName          = Core Terminal Unit Gateway
    ModelName            = Genesis
    Version              = 2.0

These values are helpful for device discovery, diagnostics, or validation in a SCADA environment.

Dynamic IP Address Resolution
"""""""""""""""""""""""""""""

.. code-block:: python

    ipAddress = getIpAddress()

This utility function fetches the device’s local IP address automatically, ensuring the gateway binds to the correct network interface. This is especially useful on devices like Raspberry Pi that may change IPs between boots.

Server Startup
"""""""""""""""

.. code-block:: python

    await StartAsyncTcpServer(context, identity=identity, address=(ipAddress, variables.modbusPort))

This launches the non-blocking Modbus TCP server:

- `context`: the Modbus server context which holds all register values.
- `identity`: the device info structure.
- `address`: a tuple of `(IP, port)`.

Once started, the server runs indefinitely within the asyncio event loop, allowing simultaneous handling of:

- Client read requests (e.g., FC3 and FC4)
- Context updates from `modbusPolling`

Port Configuration
"""""""""""""""""""

The port is sourced from the `variables` module:

.. code-block:: python

    variables.modbusPort

Ensure this value matches the port expected by your SCADA or Modbus master systems. Typical ports include `502` (default Modbus TCP) or a custom value like `5020`.

Summary
"""""""""

The `modbusServer` coroutine is the final output layer of the XBee gateway:

- It makes the internal data accessible to the outside world.
- Leverages asynchronous IO for non-blocking performance.
- Integrates seamlessly with the shared Modbus context used by other tasks.

startProcess
^^^^^^^^^^^^^

The `startProcess` coroutine serves as the centralized task coordinator for the XBee Gateway application.

Overview
"""""""""

This function:

- Initializes the Modbus register context using `contextManager` from the `modbus` module.
- Creates the background polling task for XBee data.
- Starts the main event loop that concurrently runs:
  
  - XBee serial data polling
  - Modbus context updates
  - Modbus TCP server

It is the main orchestrator that wires together the entire gateway workflow using `asyncio.gather`.

Implementation
"""""""""""""""

.. code-block:: python

    async def startProcess():
        context = contextManager()
        variables.xbeePollingTask = asyncio.create_task(xbeePolling())

        await asyncio.gather(
            variables.xbeePollingTask,
            modbusPolling(context),
            modbusServer(context)
        )

Steps Breakdown
"""""""""""""""

**1. Context Initialization**

.. code-block:: python

    context = contextManager()

`contextManager()` is a helper function defined in the `modules.modbus` module.  
It returns a `ModbusServerContext` object that holds all register blocks used in the server, including:

- Discrete Inputs (DI)
- Coils (CO)
- Holding Registers (HR)
- Input Registers (IR)

This centralized context is passed to both the `modbusPolling` task and the `modbusServer`, ensuring they operate on the same memory structure.

**2. Background Task Creation**

.. code-block:: python

    variables.xbeePollingTask = asyncio.create_task(xbeePolling())

This launches the XBee radio polling loop in the background. The returned task object is stored in `variables` to allow external cancellation or monitoring.

**3. Launch Concurrent Tasks**

.. code-block:: python

    await asyncio.gather(
        variables.xbeePollingTask,
        modbusPolling(context),
        modbusServer(context)
    )

This schedules and runs all gateway components concurrently:

- `xbeePolling` collects packets into a shared queue.
- `modbusPolling` consumes packets and updates Modbus registers.
- `modbusServer` exposes those registers over TCP.

By leveraging `asyncio.gather`, all three coroutines operate within the same event loop, eliminating the need for threading.

Concurrency Considerations
"""""""""""""""""""""""""""

Because all tasks share data structures like `xbeeQueue` and `context`, care is taken to:

- Use non-blocking I/O
- Avoid race conditions via `await`
- Share state predictably using asyncio primitives

Summary
"""""""""

The `startProcess()` function glues the system together, ensuring the XBee Gateway:

- Initializes correctly
- Runs all components in harmony
- Operates in a responsive, non-blocking manner

It is invoked by the `__main__` block when the program starts.

__main__
^^^^^^^^^

The `__main__` block is the program's entry point when the script is executed directly. It sets up the event loop, runs the gateway, and handles graceful shutdown on termination or error.

Overview
"""""""""

This block ensures that:

- The gateway is only executed when the file is not imported as a module.
- The `startProcess()` coroutine is run using `asyncio.run`.
- Any runtime errors are logged to the console.
- The XBee serial port is closed safely upon exit, preventing resource leaks.

Implementation
"""""""""""""""

.. code-block:: python

    if __name__ == "__main__":
        try:
            asyncio.run(startProcess())
        except KeyboardInterrupt:
            print(f"\nUser cancelled operation\n")
        except Exception as e:
            print(f"Unknown error with info as: {e}")
        finally:
            if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():
                variables.xbeeInstance.close()

Explanation
"""""""""""""

**1. Main Execution Guard**

.. code-block:: python

    if __name__ == "__main__":

Ensures this code block only runs when the script is executed directly (e.g., `python main.py`). Prevents unintended execution if imported as a library or module.

**2. Async Runtime Launcher**

.. code-block:: python

    asyncio.run(startProcess())

Starts the asyncio event loop and calls `startProcess()` to initialize and run all gateway tasks. This is the official way to start asynchronous programs in modern Python (`>=3.7`).

**3. Graceful Shutdown**

.. code-block:: python

    except KeyboardInterrupt:
        print(f"\nUser cancelled operation\n")

Handles user interruption (Ctrl+C) gracefully by printing a friendly message instead of a traceback.

**4. Catch-All Error Logging**

.. code-block:: python

    except Exception as e:
        print(f"Unknown error with info as: {e}")

Any unexpected errors during startup or runtime are caught and logged. This helps in debugging deployment or field issues.

**5. Resource Cleanup**

.. code-block:: python

    finally:
        if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():
            variables.xbeeInstance.close()

This block ensures that the XBee serial port is closed if it was previously opened. Prevents port locking and ensures the device can reconnect cleanly next time.

Summary
"""""""""

The `__main__` block is crucial for managing the lifecycle of the gateway. It:

- Starts the asyncio-based workflow
- Handles interruptions and crashes
- Ensures hardware resources (like serial ports) are released properly

Together with `startProcess`, it ensures a robust, fault-tolerant startup and shutdown process.


.. _configGui:

configGui
-----------

Gateway Configuration GUI
================

This Tkinter-based GUI allows users to configure the XBee network and Modbus communication settings for the gateway.

GUI Components
--------------
The interface consists of several main sections:

1. **Header Section**
    - Displays the application title
    - Shows the Modbus server IP address
    - Contains the "Configure Serial Number" button

2. **Add New Entry Section**
    - Input fields for:
        - Node Identifier
        - Radio MAC Address
        - Modbus Start Address
    - "Available Addresses" button
    - "Add to Database" button

3. **Configured XBee Radios Section**
    - Search bar with placeholder text
    - Refresh button
    - Sorting dropdown (First/Last Modified, Ascending/Descending Modbus Address)
    - Treeview table displaying configured radios with columns for:
        - S/N (Serial Number)
        - Node Identifier
        - Radio MAC Address
        - Modbus Start Address
        - Modbus End Address
    - "Delete Selected" and "Update Selected" buttons

4. **Modal Windows**
    - Available Addresses window
    - Update Entry window
    - Configuration window


Dependencies
------------

- ``tkinter``
- ``PIL.Image``, ``PIL.ImageTk``
- ``.modbus.getIpAddress``
- ``.dbIntegration`` module functions:
    - ``configureXbeeRadio``
    - ``retrieveAllConfiguredRadio``
    - ``deleteXbeeDetails``
    - ``updateXbeeDetails``
    - ``updateReusableAddress``
    - ``updateAllEndAddress``


Functions:
-----------

.. function:: get_database(self)


   Retrieves all configured radio entries from the database and inserts them into the GUI tree view. 
   If an error occurs during retrieval, an error message is shown to the user.

   This function performs the following tasks:
    - Calls the `retrieveAllConfiguredRadio()` function to fetch all radio configurations.
    - Iterates through the fetched data, inserting each entry into the GUI tree view with details such as index, item[0], item[1], item[2], and item[3].
    - If the result is a dictionary and contains an "error" key, an error message is displayed using a messagebox.

   **Example Usage:**

   .. code-block:: python

      my_object.get_database()

   **Error Handling:**

    - If the function retrieves an error message (when the result is a dictionary and contains the "error" key), the function will show an error dialog using `messagebox.showerror` with the message provided in the error field.

   **Important Notes:**
    - The `retrieveAllConfiguredRadio()` function should return a list or iterable with radio configurations, where each item is a tuple containing at least four elements. If the result is a dictionary with an "error" key, the function displays an error.



.. function:: add_database(self)


   Adds a new radio entry to the database by configuring an XBee radio with a specified radio address, Modbus address, and node identifier. 
   If successful, the tree view is updated and the input fields are cleared. If an error occurs, an error message is shown to the user.

   This function performs the following tasks:
    - Retrieves the radio address, Modbus address, and node identifier from the corresponding input fields.
    - Attempts to configure the XBee radio using the `configureXbeeRadio()` function with the provided details.
    - If the configuration is successful, clears the input fields, shows a success message, and updates the tree view by calling `get_database()` to repopulate it.
    - If there is an error during the configuration, an error message is displayed.
    - If a `ValueError` is raised due to invalid input (e.g., non-integer Modbus address), an error message is displayed.

   **Example Usage:**

   If this function is part of a class, the method can be invoked as follows:

   .. code-block:: python

      my_object.add_database()


   **Error Handling:**

   The function handles errors in the following ways:
    - **XBee Configuration Error**: If the `configureXbeeRadio()` function returns an error message, an error dialog is shown using `messagebox.showerror`.
    - **Invalid Modbus Address**: If a `ValueError` occurs due to an invalid Modbus address (non-integer value), an error dialog is shown with a specific message.

   **Important Notes:**
    - The function expects the Modbus address input to be a valid integer. If the input is not a valid integer, the function raises a `ValueError` and prompts the user to enter a valid value.
    - The `configureXbeeRadio()` function must return a dictionary, where the absence of an "error" key indicates a successful configuration, and the presence of an "error" key indicates failure.
    - After a successful entry, the tree view is cleared and repopulated using the `get_database()` function.
    - This function does not return any value.



.. function:: refresh(self)

   Refreshes the GUI by clearing and repopulating the radio configuration table and updating the displayed IP address of the Modbus server.

   This function performs the following tasks:
    - Clears all existing entries from the tree view widget.
    - Calls `get_database()` to reload and display the latest radio configuration data.
    - Retrieves the current IP address of the Modbus server using `getIpAddress()`.
    - Updates the `ip_address_label` widget to display the retrieved IP address.


   **Example Usage:**

   .. code-block:: python

      my_object.refresh()

   **Function Details:**

   - :param self: The instance of the class calling the method. (Implicit)
   - :return: This function does not return any value.

   **Important Notes:**
    - Assumes that `get_database()` repopulates the tree view with current configuration data.
    - Assumes `getIpAddress()` returns a string representing the Modbus server’s current IP address.
    - The `ip_address_label` widget must already be defined and configured in the GUI for the IP update to display correctly.



.. function:: live_search(self, event=None)

   Filters and displays tree view rows based on a live search query entered by the user in the search bar. If no matches are found, an informational dialog is shown.

   This function performs the following steps:
    - Retrieves the user's input from the search bar and converts it to lowercase.
    - Temporarily detaches all items from the tree view to prepare for filtering.
    - Iterates through stored data (`self.data`) and reattaches only the items that match the search query.
    - If no matches are found, displays a message box notifying the user.


   **Example Usage:**

   .. code-block:: python

      self.search_bar.bind("<KeyRelease>", self.live_search)

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :param event: Automatically passed by event bindings (optional).
    - :return: This method does not return a value.

   **Data Requirements:**
    - `self.data` should be a list of tuples in the form `(values, iid)`, where:
        - `values` is an iterable of displayed column values,
        - `iid` is the item identifier in the tree view.
    - `self.search_bar` should be an input widget (e.g., `Entry`) containing the search query.
    - `self.tree` should be a `ttk.Treeview` widget.

   **Behavior:**
    - The search is case-insensitive and matches substrings within any of the row values.
    - Matching rows are reattached to the tree; all others remain detached.
    - If no matches are found, a message box is shown with a “No match found” message.


.. function:: sort_table(self, event=None)

   Sorts the entries in the tree view based on the selected criterion from a dropdown menu. Sorting options include modification order and Modbus address values.

   This function performs the following tasks:
    - Retrieves the current sorting option from a dropdown selection.
    - Collects all tree view items and their associated data.
    - Sorts the data based on the selected criterion:
        - **First Modified**: Sorts by original order (ascending by `text` field(an invisible column which carries values similar to an identification number)).
        - **Last Modified**: Sorts by reverse order (descending by `text` field).
        - **Ascending Modbus Address**: Sorts entries by the Modbus address in ascending order.
        - **Descending Modbus Address**: Sorts entries by the Modbus address in descending order.
    - Reassigns serial numbers to each item based on the new order.
    - Moves each item in the tree view to reflect the sorted arrangement.


   **Example Usage:**

   .. code-block:: python

      self.dropdown.bind("<<ComboboxSelected>>", self.sort_table)

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :param event: Optional event object from GUI interactions.
    - :return: This method does not return a value.

   **Dependencies and Assumptions:**
    - `self.dropdown`: A dropdown widget (`ttk.Combobox`) used to select the sorting criterion.
    - `self.tree`: A `ttk.Treeview` widget that displays rows of data.
    - The `values` for each tree item must be a list where the 4th value (`values[3]`) represents the Modbus address.
    - The `text` field of each item is used as a sortable ID (typically representing insertion order).

   **Sorting Behavior:**
    - Each tree item’s serial number (first column value) is updated to reflect its position after sorting.
    - Items are visually reordered in the GUI using `tree.move()`.



.. function:: get_available_address(self)

   Opens a new window displaying a list of available Modbus address ranges retrieved from the backend. The data is shown in a scrollable table with columns for serial number, address range, range size, and usability.

   This function performs the following tasks:
    - Creates a new `Toplevel` window titled "Available Addresses".
    - Retrieves available address data using the `updateReusableAddress("test")` function.
    - Constructs a scrollable `ttk.Treeview` table to present the address range data.
    - Populates the table with the retrieved data.
    - If an error occurs during address retrieval, displays an error dialog using `messagebox.showerror`.


   **Example Usage:**

   .. code-block:: python

      self.get_available_address()

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :return: This method does not return a value.

   **UI Elements Created:**
    - A new `Toplevel` window (`self.available_address_window`) sized 800x300.
    - A scrollable `ttk.Treeview` (`self.tree_available`) with the following columns:
        - **S/N**: Serial number (auto-incremented).
        - **Available Range**: The Modbus address range available.
        - **Range Size**: Size of the address range.
        - **Usability**: Whether the range is consumable or not.

   **Data Source:**
    - Uses `updateReusableAddress("test")` to fetch available address ranges.
    - Expects a list of dictionaries, each containing:
        - `"modbusAddressRange"` (str),
        - `"size"` (int),
        - `"consumable"` (bool or str indicating usability).

   **Error Handling:**
    - If the response is a dictionary with an `"error"` key, an error message box is shown.

   **Notes:**
    - The function assumes that all UI elements (e.g., `tk`, `ttk`, and `messagebox`) are properly imported and available.


.. function:: delete_selected(self)

   Deletes one or more selected entries from the tree view and the backend database after user confirmation. If deletion is successful, the view is refreshed and a success message is shown.

   This function performs the following steps:
    - Retrieves selected items from the tree view.
    - If no item is selected, displays an error dialog prompting the user to select one.
    - Prompts the user with a confirmation dialog before deletion.
    - For each selected item:
        - Extracts the radio MAC address from the item's values.
        - Calls `deleteXbeeDetails()` to remove the corresponding entry from the backend.
        - If successful, deletes the item from the tree view.
        - If an error occurs during deletion, displays an error message.
    - Refreshes the UI by calling `self.refresh()` and shows a success message if deletions completed.

   **Example Usage:**

   .. code-block:: python

      self.delete_selected()

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :return: This method does not return a value.

   **User Prompts:**
    - If nothing is selected: shows `"Please select an item to delete."`
    - Before deletion: asks for confirmation via `"Are you sure you want to proceed?"`
    - After success: shows `"Entry deleted successfully."`

   **Assumptions:**
    - The third value (`values[2]`) of each tree item contains the radio MAC address.
    - `deleteXbeeDetails(mac_address)` returns a dictionary and uses an `"error"` key to indicate failure.
    - `self.refresh()` updates the view after deletion.

   **Error Handling:**
    - No selection: shows an error dialog.
    - Backend error during deletion: shows the error message in a dialog.

   **Notes:**
    - The tree view must use the `ttk.Treeview` widget.


Notes
-----

- The GUI is designed for 800x650 resolution
- All database operations are reflected immediately in the UI
- Input validation is performed for Modbus addresses
- Confirmation dialogs are shown for destructive operations



.. _dbIntegration:

dbIntegration
----------------

modbusAddressPolice
'''''''''''''''''''''''

updateReusableAddress
'''''''''''''''''''''''

updateAllEndAddress
'''''''''''''''''''''''

dbQueryModbusStartAddress
'''''''''''''''''''''''''

configureXbeeRadio
'''''''''''''''''''''''

updateXbeeDetails
'''''''''''''''''''''''

storeXbeeHistoryData
'''''''''''''''''''''''

swapXbeeHistoryAndMacAddress
'''''''''''''''''''''''''''''

deleteXbeeDetails
'''''''''''''''''''''''

retrieveAllConfiguredRadio
'''''''''''''''''''''''''''

populateDbHelper
'''''''''''''''''''''''


.. _modbus:

modbus
--------

floatToRegisters
'''''''''''''''''''''''

contextManager
'''''''''''''''''''''''

getIpAddress
'''''''''''''''''''''''

.. _serialSelector:

serialSelector
----------------

selectUsbPort
'''''''''''''''''''''''

.. _variables:

variables
------------

.. _xbeeDAta:

xbeeData
------------

getNodeId
'''''''''''''''''''''''

cayenneParse
'''''''''''''''''''''''

.. _xbeeDummyDataTransmitter:

xbeeDummyDataTransmitter
----------------------------