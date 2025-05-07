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
.. note::
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
----------

This Tkinter-based GUI allows users to configure the XBee network and Modbus communication settings for the gateway.

GUI Components
^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^

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
^^^^^^^^^^

.. function:: get_database(self)


   Retrieves all configured radio entries from the database and inserts them into the GUI tree view. 
   If an error occurs during retrieval, an error message is shown to the user.

   This function performs the following tasks:
    - Calls the `retrieveAllConfiguredRadio()` function to fetch all radio configurations.
    - Iterates through the fetched data, inserting each entry into the GUI tree view with details such as index, item[0], item[1], item[2], and item[3].
    - If the result is a dictionary and contains an "error" key, an error message is displayed using a messagebox.

   **Example Usage:**

   .. code-block:: python

      self.get_database()
    

   **Function Details:**

    - :param self: The instance of the class calling the method. (Implicit)
    - :return: This function does not return any value. 

   **Error Handling:**

    - If the function retrieves an error message (when the result is a dictionary and contains the "error" key), the function will show an error dialog using `messagebox.showerror` with the message provided in the error field.

   **Notes:**
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

      self.add_database()


   **Function Details:**

   - :param self: The instance of the class calling the method. (Implicit)
   - :return: This function does not return any value.

   **Error Handling:**

   The function handles errors in the following ways:
    - **XBee Configuration Error**: If the `configureXbeeRadio()` function returns an error message, an error dialog is shown using `messagebox.showerror`.
    - **Invalid Modbus Address**: If a `ValueError` occurs due to an invalid Modbus address (non-integer value), an error dialog is shown with a specific message.

   **Notes:**
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

      self.refresh()

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


.. function:: update_selected(self)

   Opens a form to update the selected entry in the tree view. Pre-fills the form with existing data, and waits for user input to complete the update.

   This function performs the following steps:
    - Checks whether a tree item is selected. If not, displays an error message.
    - Disables the update button to prevent multiple update windows.
    - Opens a new `Toplevel` window titled "Update Entry".
    - Builds an entry form with fields for:
        - Node Identifier
        - Radio MAC Address
        - Modbus Start Address
        - Modbus End Address
    - Pre-fills these input fields with the current values from the selected item.
    - Binds the window close protocol to `self.close_window` and waits until the window is closed before re-enabling the update button.


   **Example Usage:**

   .. code-block:: python

      self.update_button.config(command=self.update_selected)

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :return: This method does not return a value.

   **UI Elements Created:**
    - A modal `Toplevel` window named `self.update_window`.
    - Four labeled input fields for updating node, MAC address, and Modbus addresses.
    - A button labeled "Update Entry" that calls `self.click_update`.

   **Data Handling:**
    - Uses `self.tree.item(self.selected_item)["values"]` to extract:
        - `values[1]`: Node Identifier
        - `values[2]`: Radio MAC Address
        - `values[3]`: Modbus Start Address
        - `values[4]`: Modbus End Address
    - These values are inserted into their corresponding entry fields for user editing.

   **Window Behavior:**
    - The main window waits for the update window to close before continuing.
    - Update button (`self.update_button`) is disabled while the update window is open and re-enabled afterward.
    - The close action is bound to a custom cleanup method (`self.close_window`).

   **Error Handling:**
    - If no item is selected in the tree, an error message is shown: "Please select an item to update."

   **Assumptions:**
    - `self.tree` is a `ttk.Treeview` with at least 5 columns in each row.
    - `self.click_update()` and `self.close_window()` are defined elsewhere in the class.


.. function:: click_update(self)

   Applies the updates specified in the update entry form and updates the backend database accordingly.

   This function performs the following actions:
    - Retrieves new values entered by the user in the update form.
    - Compares the new values to the previously stored values.
    - Builds a dictionary (`self.json_data`) with only the fields that have changed.
    - If changes are detected:
        - Prompts the user for confirmation showing a summary of the updates.
        - Sends the update data to the backend using `updateXbeeDetails`.
        - If successful, refreshes the main table view, displays a success message, and closes the update window.
        - If an error occurs, displays the error message.
    - If no changes are detected, shows an error and closes the update window.


   **Example Usage:**

   .. code-block:: python

      self.click_update()

   **Function Details:**

    - :param self: The instance of the class calling the method.
    - :return: This method does not return a value.

   **Key Variables:**
    - `self.json_data`: A dictionary containing only updated fields.
    - `self.result`: A list of human-readable change summaries.


   **Update Workflow:**
    - Compares new inputs against old values:
        - `xbeeNodeIdentifier`
        - `xbeeMac`
        - `modbusStartAddress`
        - `modbusEndAddress`
    - Only modified fields are sent in the update request.
    - A confirmation dialog shows the user what will change before proceeding.

   **Backend Interaction:**
    - Uses `updateXbeeDetails(mac_address, json_data)` to update the device configuration.
    - A successful response is expected to have no `"error"` key.

   **User Prompts:**
    - If updates are found: prompts with "Are you fine with this update?" and shows details.
    - If no changes are found: shows "No new update detected."
    - On success: shows "Entry updated successfully."
    - On error: shows the error message from the backend.

   **Assumptions:**
    - All entry widgets (`self.node_input`, etc.) are valid and exist.
    - `self.old_*` attributes are set beforehand (typically from `update_selected()`).
    - `self.refresh()` refreshes the tree view, and `self.close_window()` cleans up the modal.

   **Error Handling:**
    - Backend errors are shown via `messagebox.showerror`.
    - If no changes are detected, user is informed and the update window is closed.


.. function:: configure_button(self)

   Opens the configuration window and preloads settings from a local Python module file called `variables.py`.

   This function performs the following actions:
    - Opens and reads the contents of `modules/variables.py`.
    - Extracts values for:
        - `prefferedRadioSerialNumber`
        - `modbusPort`
        - `incrementalModbusAddress`
    - Displays a new configuration window with input fields for these values.
    - Pre-fills the fields with the values read from the file.
    - Adds a **Save** button that triggers `self.read_serial_and_modbusport` when clicked.


   **Example Usage:**

   .. code-block:: python

      self.configure_button()


   **Function Workflow:**

    - Opens the `modules/variables.py` file and searches for:
        - `prefferedRadioSerialNumber`
        - `modbusPort`
        - `incrementalModbusAddress`
    - Extracts the values, strips quotation marks and whitespace as needed.
    - Creates a `tk.Toplevel` window titled *Configuration Window*.
    - Adds `tk.Entry` widgets for each extracted setting, pre-filled with current values.
    - Places a **Save** button that calls `read_serial_and_modbusport`.



   **Dependencies:**

    - Assumes the file `modules/variables.py` exists and contains the target variables.
    - Relies on the method `read_serial_and_modbusport` to handle saving updated settings.

    **Potential Exceptions:**

    - If the `modules/variables.py` file is missing or unreadable, a `FileNotFoundError` or `IOError` may be raised.
    - If any of the expected variables are missing from the file, corresponding inputs will be empty.

   **Notes:**

    - This function does **not** save changes itself—it only reads and displays current settings.
    - The actual save logic is delegated to `read_serial_and_modbusport`.


.. function:: read_serial_and_modbusport(self)

   Updates configuration variables in the `modules/variables.py` file based on user input from the configuration GUI.

   This method performs the following tasks:
    - Reads current values from `modules/variables.py`.
    - Compares them to user-provided inputs in the GUI.
    - If any changes are detected:
        - Updates the file with new values.
        - Optionally updates all Modbus end addresses if the incremental value changed.
    - Displays appropriate message dialogs to confirm and report results.



   **Example Usage:**

   .. code-block:: python

      self.read_serial_and_modbusport()

   **Process Overview:**

    - Reads the file `modules/variables.py` line-by-line.
    - Compares the following variables:
        - `prefferedRadioSerialNumber`
        - `modbusPort`
        - `incrementalModbusAddress`
    - For each variable that differs from the old value:
        - Constructs a new line.
        - Updates the corresponding line in memory.
        - Appends the change to a result list for display.
    - If `incrementalModbusAddress` changed, prompts the user to update all Modbus end addresses via `updateAllEndAddress()`.

   **GUI Interaction:**
    - Prompts user to confirm changes via `messagebox.askyesno`.
    - On update success, shows `messagebox.showinfo`.
    - If no change detected, shows `messagebox.showerror`.

   **Dependencies:**
    - Requires file `modules/variables.py` to exist and be writable.
    - Calls external method `updateAllEndAddress(new_incremental_address)` if `incrementalModbusAddress` is updated.
    - Calls `self.refresh()` after a successful update and optional end address update.

   **Raises:**
    - `ValueError` if GUI input cannot be cast to integers.
    - `FileNotFoundError` or `IOError` if file access fails.

   **Notes:**
    - Closes the configuration window (`self.configure_window`) after execution.
    - Does not rollback changes if an error occurs after writing the file.


.. function:: clear_placeholder(self, event)

   Clears the placeholder text from the search bar input field when it gains focus.

   This method is typically bound to the `<FocusIn>` event of the search bar widget. When the field is focused and the default placeholder text ("Search here") is present, it removes the placeholder and sets the text color to black.

    :param event: The event object triggered by the GUI (usually `<FocusIn>`).
    :type event: tkinter.Event


   **Example Binding:**

   .. code-block:: python

      self.search_bar.bind("<FocusIn>", self.clear_placeholder)

   **Behavior:**

    - Checks if the current text in the `search_bar` is `"Search here"`.
    - If so:
        - Clears the input field.
        - Changes the text color to black (default typing color).

   **Used For:**
    - Enhancing user experience by managing placeholder behavior in entry fields.

   **Dependencies:**
    - Assumes `self.search_bar` is a `tk.Entry` widget.



.. function:: add_placeholder(self, event)

   Adds a placeholder text to the search bar if the field is empty.

   This method is usually bound to the `<FocusOut>` event of the search bar widget. When the entry field loses focus and is empty, it inserts a default placeholder text ("Search here") and changes the text color to grey to indicate it's a placeholder.

    :param event: The event object triggered by the GUI (usually `<FocusOut>`).
    :type event: tkinter.Event


   **Example Binding:**

   .. code-block:: python

      self.search_bar.bind("<FocusOut>", self.add_placeholder)

   **Behavior:**

    - Checks if the `search_bar` field is currently empty.
    - If so:
        - Inserts the text `"Search here"`.
        - Sets the text color to grey.

   **Used For:**
    - Providing user-friendly guidance in input fields with placeholder text.

   **Dependencies:**
    - Assumes `self.search_bar` is a `tk.Entry` widget.

Notes
^^^^^^

- The GUI is designed for 800x650 resolution
- All database operations are reflected immediately in the UI
- Input validation is performed for Modbus addresses
- Confirmation dialogs are shown for destructive operations
- All functions return `None` unless otherwise specified



.. _dbIntegration:

dbIntegration
----------------

This module manages all MongoDB-related operations for the XBee Modbus Gateway system. It handles:

- Configuration, validation, and updating of XBee radio metadata such as MAC addresses, Modbus start/end addresses, and node identifiers.
- Ensuring Modbus address allocation is valid and conflict-free using range validation and gap detection.
- Updating and retrieving reusable Modbus address ranges for dynamic allocation.
- Managing historical data storage for each XBee radio, supporting initialization, updates, and full data swaps in cases of MAC address reassignment.
- Providing database interfaces for querying and modifying the Modbus address map and XBee radio assignments.

.. note::
    The MongoDB schema is optimized for time-series storage, and each XBee device is
    tracked using its 64-bit MAC address.

Module Setup
^^^^^^^^^^^^

Modules & Dependencies
"""""""""""""""""""""""

The following standard and third-party modules are imported:

- ``datetime``, ``random``, ``string``:  
  Core Python modules used for timestamps, ID generation, and text manipulation.

- ``pymongo``, ``pymongo.errors.PyMongoError``:  
  MongoDB driver for Python and exception handling for database operations.

Application-specific modules:

- ``modules.variables``:  
  Stores shared runtime variables and configuration constants.

- ``modules.modbus``:  
  Provides:
  
  - ``getIpAddress``: Retrieves the current IP address of the device, used to bind the MongoDB client to the local network interface.

MongoDB Collections
""""""""""""""""""""

Two main MongoDB collections are initialized:

- ``configuredRadioCollection``:  
  Stores metadata for each configured XBee device, such as MAC address, Modbus address range, and human-readable identifier.

- ``availableModbusAddressCollection``:  
  Maintains a list of reusable Modbus address ranges freed after device deletion or reallocation.


Database Initialization
"""""""""""""""""""""""

- ``dbclient = pymongo.MongoClient(...)``:  
  Initializes the MongoDB client connection using the host IP determined by ``getIpAddress()`` from ``modules.modbus``.

- ``gatewaDb = dbclient["Gateway"]``:  
  References the main MongoDB database used by the gateway system.

modbusAddressPolice
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    modbusAddressPolice(proposedStartAddress, supposedEndAddress)

Validates whether a given Modbus address range is available and conforms to system constraints.

   This function checks whether a proposed range of Modbus register addresses is:
   - within allowable numeric bounds,
   - not overlapping with any existing Modbus address ranges already registered in the system,
   - and structurally valid according to defined system-wide rules.

   It is typically used during the configuration or onboarding of new XBee radio nodes to ensure
   that each device is mapped to a safe and unique holding register range in the Modbus server context.

   :param int proposedStartAddress: 
       The first Modbus holding register address being proposed for 
       assignment (e.g., 40001).

   :param int supposedEndAddress: 
       The last Modbus holding register address (inclusive) being 
       proposed.

   :returns: 
       Returns a validation result object:

       - ``True`` — if the proposed range is valid and available.
       - ``{"error": "<reason>"}`` — if the proposed range is invalid or would conflict with existing addresses.

   :rtype: Union[bool, dict]

Validation Logic
""""""""""""""""""

   - The start address must be less than or equal to the end address.
   - The length (number of digits) of the start address must conform to the `validModbusAddressLength` constraint defined in `variables`.
   - The range must fall within bounds set by `variables.lowestRegister` and `variables.highestRegister`.
   - The address range must not overlap with any existing ranges stored in the `configuredRadioCollection` MongoDB collection.

Overlapping Address Rule:
""""""""""""""""""""""""""

   Two address ranges are considered overlapping if:

   .. code-block:: text

      proposedStart <= existingEnd and proposedEnd >= existingStart

Example Usage:
""""""""""""""

   .. code-block:: python

      result = modbusAddressPolice(40021, 40040)
      if result is True:
          print("Modbus address range is valid.")
      else:
          print("Address validation failed:", result["error"])

Error Response Format:
""""""""""""""""""""""

   When validation fails, the function returns a dictionary of the form:

   .. code-block:: json

      {
         "error": "Descriptive error message"
      }

Typical Errors:
""""""""""""""""

   - "Start address cannot be greater than end address"
   - "Invalid modbus address"
   - "Modbus address out of range"
   - "Could not update: Selected modbus startAddress would cause address overlapping"
   - Any internal exception is returned as an error string

Dependencies:
""""""""""""""

   - Uses global `variables` module to access:
     - `lowestRegister`
     - `highestRegister`
     - `validModbusAddressLength`
   - Reads from `configuredRadioCollection`, a MongoDB collection containing all configured devices and their Modbus address ranges.


updateReusableAddress
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    updateReusableAddress(returnData=None)

Scans configured Modbus address allocations and updates the database with all available (unused) address ranges.

   This utility function is essential for maintaining visibility into unallocated Modbus holding register blocks. It identifies address gaps between already-configured devices and updates the `availableModbusAddressCollection` accordingly. The available ranges can then be reused when configuring new XBee devices.

   :param bool returnData:

       Optional. If set, the function returns the list of available address blocks as a list of dictionaries.
       If `None` (default), the function runs silently and only populates the database.

      :returns:

       - If `returnData` is `None`, returns `None`.

       - If address gaps are found, returns a list of available range objects:

         .. code-block:: json

            [
                {
                    "modbusAddressRange": "4010-4030",
                    "size": 21,
                    "consumable": "✅"
                }
            ]

       - If no address gaps exist, returns:

         .. code-block:: json

            { "info": "No available address gaps found." }

       - If an error occurs, returns a dictionary with `error` and optional `details`.

   :rtype: Union[None, list, dict]


Function Overview
""""""""""""""""""

   This function performs the following steps:

   1. **Drops the `availableModbusAddressCollection`** to clear outdated data.
   2. **Retrieves all configured address ranges** from `configuredRadioCollection`.
   3. **Sorts** the address ranges by `modbusStartAddress`.
   4. **Scans for gaps** between configured ranges:
      - A "gap" is defined as an unused range between two allocated address blocks.
      - Gaps are considered **consumable** if their size is greater than or equal to `variables.incrementalModbusAddress`.
   5. **Stores valid gaps** in `availableModbusAddressCollection`, each with:
      - `modbusAddressRange`: The range in "start-end" format.
      - `size`: Number of registers in the gap.
      - `consumable`: "✅" if usable, "❌" otherwise.
   6. **Optionally returns the result** if `returnData` is specified.

Gap Detection Algorithm
""""""""""""""""""""""""

   Gaps are identified by comparing the `endAddress` of a configured device with the `startAddress` of the next:

   .. code-block:: python

      if startAddress - previousEnd > 1:
          gapStart = previousEnd + 1
          gapEnd = startAddress - 1

   The final unallocated range (from the last used address to the highest possible register) is also checked.

Consumable Criteria
""""""""""""""""""""

   A gap is marked as **consumable** (`✅`) only if:

   .. code-block:: python

      gapSize >= variables.incrementalModbusAddress

   Otherwise, it is marked as **not consumable** (`❌`).

Error Handling
""""""""""""""

   - MongoDB `insert_one` failures are caught and returned with detailed error messages.
   - General exceptions are caught and returned with an `"error"` key.

Dependencies
"""""""""""""

   - MongoDB collections:

     - `configuredRadioCollection` (read-only)
     - `availableModbusAddressCollection` (dropped and written)

   - Variables from the `variables` module:

     - `lowestRegister`
     - `highestRegister`
     - `incrementalModbusAddress`

   - Requires `PyMongoError` for database exception handling.

Example
"""""""

   .. code-block:: python

      # Run silently
      updateReusableAddress()

      # Run and fetch results for further processing
      availableBlocks = updateReusableAddress(returnData=True)
      for block in availableBlocks:
          print(block["modbusAddressRange"], block["consumable"])

updateAllEndAddress
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python
    
    updateAllEndAddress(newRange)

Recalculates and updates the `modbusEndAddress` field for all configured radios using a uniform range size derived from the provided `newRange` value.

   This function is useful when there's a global change in how many Modbus registers should be allocated per device. It ensures all documents in the `configuredRadioCollection` reflect this new register allocation model, based on their existing `modbusStartAddress`.

   :param int newRange:

       The number of Modbus registers to assign per device. The function adds `(newRange - 1)` to each device's `modbusStartAddress` to compute the new `modbusEndAddress`.

   :returns:

       - If updates are made:

         .. code-block:: json

            { "sucess": "updated 25" }

         (Where 25 is the number of documents updated.)

       - If an error occurs during the update operation:

         .. code-block:: json

            { "error": "Descriptive error message" }

       - If no `modbusStartAddress` is found, or no documents are modified, returns `None`.

   :rtype: Union[dict, None]

Functional Summary
""""""""""""""""""

This function:

   1. **Queries all radio documents** from `configuredRadioCollection` that have a `modbusStartAddress`.
   2. **Calculates** the new `modbusEndAddress` for each document as:

      .. code-block:: python

         newEndAddress = startAddress + (newRange - 1)

   3. **Performs a batch update** using `bulk_write()` with `UpdateOne` operations to apply changes efficiently.
   4. **Calls `updateReusableAddress()`** to refresh available address blocks after modifications.
   5. **Returns** the number of modified documents or an error response.

Error Handling
"""""""""""""""

   - All exceptions are caught and returned as a dictionary with an `error` key.
   - If the `bulk_write()` operation fails or modifies nothing, the function silently returns `None`.

Dependencies
""""""""""""""
   - MongoDB collection:

     - `configuredRadioCollection` (read and write)

   - External function:

     - `updateReusableAddress()` — called after successful updates to refresh available address gaps.

   - Libraries:

     - `pymongo.UpdateOne` and `bulk_write`

Performance Note
""""""""""""""""

   - The use of `bulk_write()` ensures efficient updating even for large numbers of documents.
   - The function assumes the presence of a valid `modbusStartAddress` in each document.

Example Usage
""""""""""""""

   .. code-block:: python

      # Update all configured radios to use 20 Modbus registers each
      result = updateAllEndAddress(newRange=20)
      print(result)

Related Functions
""""""""""""""""""

   - :func:`updateReusableAddress` — updates the list of reusable Modbus address gaps based on current configurations.

dbQueryModbusStartAddress
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    dbQueryModbusStartAddress(xbeeMacAddress)

Retrieves the configured Modbus start address for a given XBee MAC address from the database.

This function performs a lookup in the ``configuredRadioCollection`` to find the ``modbusStartAddress`` associated with a specific XBee radio. It is typically used during Modbus polling to determine where sensor data from each radio should be written in the Modbus context.

:param str xbeeMacAddress:
    The 64-bit MAC address of the XBee device, provided as a string. The function automatically converts the address to uppercase to match the format stored in the database.

:returns:
    - If the MAC address exists in the database, returns the integer value of ``modbusStartAddress``.
    - If the MAC address is not found, returns a string indicating that the address is missing.
    - If an exception occurs, prints the error and returns it as a string.

:rtype: Union[int, str]

Function Overview
""""""""""""""""""

This function executes the following steps:

1. Converts the provided MAC address to uppercase.
2. Searches the ``configuredRadioCollection`` for a matching ``xbeeMac`` value.
3. If a matching document is found, extracts and returns the ``modbusStartAddress``.
4. If no document is found, returns a descriptive message.
5. Catches and prints any exceptions, returning the error message.

Usage Context
""""""""""""""

This function is called inside the Modbus polling logic to determine the register block for each XBee:

.. code-block:: python

    startAddress = dbQueryModbusStartAddress(mac)
    if isinstance(startAddress, int):
        contextValue[0].setValues(3, startAddress, registers)
        contextValue[0].setValues(4, startAddress, registers)

Error Handling
""""""""""""""

- Wraps all logic in a try-except block.
- On failure, prints the error message and returns it.
- Ensures the main polling loop remains stable during faults.

Dependencies
"""""""""""""

- MongoDB collection:

  - ``configuredRadioCollection`` — stores XBee device configurations and associated Modbus address mappings.

Example
"""""""

.. code-block:: python

    mac = "0013A20040B41234"
    startAddress = dbQueryModbusStartAddress(mac)

    if isinstance(startAddress, int):
        print(f"Start address: {startAddress}")
    else:
        print(f"Error or not found: {startAddress}")


configureXbeeRadio
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    configureXbeeRadio(xbeeMacAddress, startAddress, nodeIdentifier)

Registers a new XBee radio device in the system by associating it with a unique MAC address, Modbus register block, and node identifier.

   This function performs comprehensive validation to ensure no conflicts exist in the configured Modbus address space or device identifiers. It calculates the Modbus **end address internally** using the formula:

   .. code-block:: python

      endAddress = startAddress + (variables.incrementalModbusAddress - 1)

   On success, it updates the database and creates a dedicated collection for storing historical data for that device.

   :param str xbeeMacAddress:
       The 64-bit MAC address of the XBee radio to configure (e.g., ``0013A20040B2C3D4``). Must be uppercase and 16 characters long.

   :param int startAddress:
       The starting Modbus register address for this device. Must be an integer and not conflict with existing device ranges.

   :param str nodeIdentifier:
       A unique, human-readable label for the device (e.g., ``WELLHEAD_A01``). Cannot be empty or reused.

   :returns:
       - On success:

         .. code-block:: json

            { "success": "radio configured successfully" }

       - On validation failure (e.g., duplicates, format errors):

         .. code-block:: json

            { "error": "Start address already utilized by WELLHEAD_A01" }

       - On general exception:

         .. code-block:: json

            { "error": "Exception message" }

   :rtype: dict

Address Calculation
"""""""""""""""""""

- The function automatically derives the Modbus `endAddress` using:

  .. code-block:: python

     endAddress = startAddress + (variables.incrementalModbusAddress - 1)

- This defines the register block [startAddress, endAddress] inclusive.

Validation Logic
"""""""""""""""""

1. **MAC Address:**
   - Must be uppercase and 16 characters long.
   - Must not already exist in `configuredRadioCollection`.

2. **Start Address:**
   - Must be a valid integer.
   - Must not be already used as a start address.
   - Must not overlap with any existing Modbus block (validated by `modbusAddressPolice()`).

3. **Node Identifier:**
   - Cannot be empty.
   - Must be unique across configured devices.

Configuration Actions
""""""""""""""""""""""

- Inserts the following document into `configuredRadioCollection`:

  .. code-block:: json

     {
       "xbeeNodeIdentifier": "NODE1",
       "xbeeMac": "0013A20040B2C3D4",
       "modbusStartAddress": 4001,
       "modbusEndAddress": 4050
     }

- Creates a MongoDB collection named after the MAC address (e.g., `0013A20040B2C3D4`) for storing historical radio data. The collection is seeded with:

  .. code-block:: json

     {
       "timestamp": "2025-05-06T12:00:00",
       "data": [0, 0, 0, 0, 0, 0, 0, 0, 0]
     }

- Triggers a call to `updateReusableAddress()` to recalculate and store the list of free Modbus address blocks.

Dependencies
""""""""""""

- MongoDB Collections:
  - `configuredRadioCollection`
  - `gatewayDb[<xbeeMacAddress>]` (dynamic collection for history)
- Functions:
  - `modbusAddressPolice()`
  - `updateReusableAddress()`
- Constants from `variables`:
  - `validMacAddressLength`
  - `incrementalModbusAddress`

Example
"""""""

.. code-block:: python

   configureXbeeRadio("0013A20040B2C3D4", 4001, "WELLHEAD_A01")

updateXbeeDetails
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    updateXbeeDetails(oldXbeeMacAddress, jsonParameterToBeUpdated)

Updates specific fields of an already-configured XBee radio entry, with full validation of MAC address uniqueness, Modbus register allocation correctness, and node identifier exclusivity.

   This function allows updating one or more of the following fields for an existing device:

   - ``xbeeMac`` (MAC address)
   - ``modbusStartAddress``
   - ``modbusEndAddress``
   - ``xbeeNodeIdentifier``

   Updates are only accepted if no conflicts exist in the system, and the modified values differ from the existing values. 
   If address-related fields are modified, the `updateReusableAddress()` utility is automatically triggered to refresh available register gaps. Additionally, if a MAC address is changed, the function **renames the associated historian collection** to match the new MAC.

   :param str oldXbeeMacAddress:

       The current MAC address of the XBee device to update. 
       Must already exist in the `configuredRadioCollection`.

   :param dict jsonParameterToBeUpdated:

       A dictionary containing one or more keys to update. 
       Only the following keys are allowed:
       
       - ``xbeeMac`` (str)
       - ``modbusStartAddress`` (int)
       - ``modbusEndAddress`` (int)
       - ``xbeeNodeIdentifier`` (str)

   :returns:
       - On success:

         .. code-block:: json

            { "success": "Document updated successfully." }

       - On validation failure:

         .. code-block:: json

            { "error": "new mac address already exist" }

       - On redundant request (no change detected):

         .. code-block:: json

            { "error": "Update request received, but no changes were made." }

       - On general exception:

         .. code-block:: json

            { "error": "Exception message" }

   :rtype: dict

Input Validations
""""""""""""""""""

- ``jsonParameterToBeUpdated`` must be a `dict`. Otherwise:

  .. code-block:: json

     { "error": "Structure of updated value is invalid. Expected a dictionary." }

- Only the allowed keys are permitted. If unknown keys are found:

  .. code-block:: json

     { "error": "Invalid keys found: ['badKey']. Allowed keys: [...]" }

MAC Address Update
"""""""""""""""""""

- Validates that the new MAC:

  - Is 16 characters long (as per `variables.validMacAddressLength`)
  - Is different from the existing MAC
  - Does not already exist in the system

- If valid:

  - The existing historian collection under `gatewayDb[oldXbeeMacAddress]` is **renamed** to the new MAC.

Modbus Address Update
""""""""""""""""""""""

- If either `modbusStartAddress` or `modbusEndAddress` is updated:

  - The function resolves both values, using provided ones or falling back to existing ones.
  - The range is validated using `modbusAddressPolice(start, end)`.
  - If valid, the update is flagged to **refresh address gaps** via `updateReusableAddress()` after DB update.

Node Identifier Update
""""""""""""""""""""""""

- The new identifier:

  - Must not be empty.
  - Must be different from the existing one.
  - Must not be already used by another radio.

Update Workflow
"""""""""""""""""

1. Normalize all string inputs to uppercase.
2. Validate each requested change:

   - MAC → uniqueness and length
   - Modbus → address overlap prevention
   - Node ID → uniqueness and validity

3. Perform atomic update via:

   .. code-block:: python

      configuredRadioCollection.update_one({"xbeeMac": oldXbeeMacAddress}, {"$set": updates})

4. If a Modbus address was changed:

   - Call `updateReusableAddress()` to recalculate and store new available blocks.

Side Effects
""""""""""""""

- Historian collection is **renamed** if MAC is updated.
- Modbus address availability is **recalculated** if start/end address is changed.

Dependencies
"""""""""""""

- MongoDB collections:

  - `configuredRadioCollection`
  - `gatewayDb[<xbeeMac>]` (for renaming historian)

- Internal functions:

  - `modbusAddressPolice()`
  - `updateReusableAddress()`

- Variables from `variables`:

  - `validMacAddressLength`

Example
""""""""

.. code-block:: python

   # Update MAC address and start address
   updateXbeeDetails("0013A20040B2C3D4", {
       "xbeeMac": "0013A20040B2C3D9",
       "modbusStartAddress": 4060
   })

   # Update only node identifier
   updateXbeeDetails("0013A20040B2C3D4", {
       "xbeeNodeIdentifier": "WELLHEAD_B07"
   })

storeXbeeHistoryData
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   storeXbeeHistoryData(xbeeMacAddress, xbeeData, xbeeDataTimestamp)

Stores a timestamped data snapshot from an XBee device into a dedicated MongoDB historian collection named after the XBee MAC address.

   This function is intended to be called whenever a new packet of radio sensor data is received. It verifies the MAC address has been configured, ensures the data is correctly structured as a list, and inserts it into a corresponding MongoDB collection (one collection per radio, named by MAC).

   :param str xbeeMacAddress:
       MAC address of the radio node. Must match a previously configured device in `configuredRadioCollection`.

   :param list xbeeData:
       List of sensor or telemetry values received from the XBee device. Must be of list type.

   :param datetime xbeeDataTimestamp:
       A `datetime` object representing when the data was received. Used as the timestamp for the inserted document.

   :returns:
       - ``True`` on successful insertion into the historian collection.
       - ``None`` on validation failure, database failure, or unexpected exceptions.

   :rtype: bool | None

Input Normalization and Validation
"""""""""""""""""""""""""""""""""""

1. **MAC Normalization**:
   - MAC address is converted to uppercase with ``str(xbeeMacAddress).upper()``.

2. **MAC Existence Check**:
   - The function checks if the MAC is registered in `configuredRadioCollection`:
     
     .. code-block:: python

        configuredRadioCollection.find_one({"xbeeMac": xbeeMacAddress})

   - If not found, the function logs an error and exits early.

3. **Data Type Validation**:
   - Ensures `xbeeData` is a Python list. If not, it logs the type mismatch and exits.

Historian Collection Behavior
"""""""""""""""""""""""""""""""

- A historian collection is automatically created or reused using:

  .. code-block:: python

     xbeeHistoryEntry = gatewayDb[xbeeMacAddress]

  This ensures:
  - Each XBee device gets its own dedicated collection.
  - The collection name is the uppercase MAC string (e.g., `0013A20040B2C3D4`).

Document Structure Example:
""""""""""""""""""""""""""""

The inserted document has the structure:


.. code-block:: json

    [
        {
        "timestamp": "2025-05-06T14:33:21.832000",
        "data": [23.4, 1, 0, 55.6, "more"]
        }
    ]

This allows efficient time-series querying and historical graphing.

Failure Modes
"""""""""""""""

- **Unregistered MAC address**:
  
  Logs:

  .. code-block:: none

     Mac Address has not been configured

  Returns: ``None``

- **Data is not a list**:

  Logs:

  .. code-block:: none

     Expected data <xbeeData> should be passed as list

  Returns: ``None``

- **MongoDB insertion fails**:

  Logs:

  .. code-block:: none

     Could not update the database

  Returns: ``None``

- **Unhandled exception**:

  Logs:

  .. code-block:: none

     Fatal error with details as; <exception string>

  Returns: ``None``

Dependencies
""""""""""""""

- **MongoDB collections**:
  - `configuredRadioCollection`: Verifies MAC address registration.
  - `gatewayDb[<xbeeMac>]`: Target collection for historian entries.

Example Usage
""""""""""""""

.. code-block:: python

   storeXbeeHistoryData(
       "0013A20040B2C3D4",
       [78.2, 1, 0, 33.5, 9.8, 0, 1, 1],
       datetime.datetime.utcnow()
   )

Notes
"""""""

- This function assumes that the historian collections have been initialized via `configureXbeeRadio()`.
- It does **not** check for data schema conformity (e.g., number or type of elements in `xbeeData`) beyond requiring a list.


swapXbeeHistoryAndMacAddress
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   swapXbeeHistoryAndMacAddress(firstXbeeMacAddress, secondXbeeMacAddress)

Swaps the XBee MAC addresses and historical data collections between two configured radios. This function is useful in real-world scenarios where physical XBee devices are swapped between two locations.

   Instead of using `updateXbeeDetails()`, which would raise a duplication error when changing MAC addresses, this function handles the swap cleanly by also exchanging the corresponding historian collections, ensuring historical data continuity.

   :param str firstXbeeMacAddress:
       The MAC address of the first configured XBee device (before the swap).

   :param str secondXbeeMacAddress:
       The MAC address of the second configured XBee device (before the swap).

   :returns:
       - ``{"success": "Document updated successfully."}`` if swap was successful.
       - ``{"error": "<reason>"}`` if an error occurs or inputs are invalid.

   :rtype: dict

Purpose and Use Case
""""""""""""""""""""""

This function is specifically designed for **field operations** where:
- Two XBee radios (e.g., installed at well A and well B) are physically swapped.
- The MAC addresses are now mismatched with their original Modbus start addresses and historian data.
- Directly calling `updateXbeeDetails()` would violate uniqueness constraints for MACs.

Instead, `swapXbeeHistoryAndMacAddress()`:
1. Swaps their MAC entries in the `configuredRadioCollection`.
2. Swaps their historian collections in the MongoDB database.

Validation and Normalization
""""""""""""""""""""""""""""""

1. Both input MACs are normalized to uppercase.
2. The function verifies that **both MACs exist** in the `configuredRadioCollection`:

   .. code-block:: python

      configuredRadioCollection.find_one({"xbeeMac": <mac>})

   If either MAC is unregistered, an error is returned.

MongoDB Rename Mechanism
""""""""""""""""""""""""""

Historian collections (one per MAC) are renamed:

.. code-block:: python

   gatewayDb[firstMac].rename(secondMac)
   gatewayDb[secondMac].rename(firstMac)

**Important**:
- MongoDB `rename()` swaps the collection name while keeping its contents.
- This effectively **swaps the historical data** stored under each MAC.
- No data is lost or duplicated.

MAC Field Swapping in Database
"""""""""""""""""""""""""""""""

The configured MAC address values in `configuredRadioCollection` are updated accordingly:

.. code-block:: python

   {"$set": {"xbeeMac": <new_value>}}

Two `update_one()` operations are run—one per MAC.

Success & Error Handling
"""""""""""""""""""""""""

- If both `update_one()` operations modify exactly one document each, a success is returned.
- If no changes are detected, an appropriate error is returned.

Unhandled exceptions (e.g., from rename conflicts or database access issues) are caught and returned as:

.. code-block:: json

   {"error": "<exception message>"}

Notes
"""""""

- This function **does not validate** the structure of historian data itself—it assumes the format is consistent.
- It is designed to be used **only after both MACs have been configured**.
- This operation is **atomic in intent but not transactional**, so if the rename or update fails midway, manual recovery may be needed.

Example Usage
""""""""""""""

.. code-block:: python

   swapXbeeHistoryAndMacAddress("0013A20040B2C3D4", "0013A20040B2C3A9")

   # Outcome: 
   # - Historical data collections of the two radios are swapped
   # - MACs are exchanged in the radio mapping config


deleteXbeeDetails
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   deleteXbeeDetails(xbeeMacAddress)

Deletes a configured XBee radio device and its associated historical data from the system. This function performs a **full cleanup** — removing both the configuration entry and the corresponding MongoDB historian collection.

   :param str xbeeMacAddress:
       The MAC address of the XBee radio to be deleted. It is case-insensitive and automatically converted to uppercase internally.

   :returns:
       - ``{"success": "Deleted <MAC> and it's history data successfully."}`` if the operation succeeds.
       - ``{"error": "<reason>"}`` if the MAC address is not found or an error occurs.

   :rtype: dict

Overview
""""""""""

This function is used to **unregister a previously configured XBee radio**, including:

- Removing its entry from the `configuredRadioCollection` which stores MAC address, Modbus start/end addresses, and node identifiers.
- Dropping its MongoDB historian collection (named using the MAC address) which stores timestamped sensor data.

It is useful when:

- A radio is permanently removed from the field.
- Configuration needs to be reset before re-adding.
- Storage optimization is necessary (e.g., clearing unused history collections).

Validation and Preparation
""""""""""""""""""""""""""""

1. The input MAC is converted to uppercase:

   .. code-block:: python

      xbeeMacAddress = str(xbeeMacAddress).upper()

2. The MAC is checked for existence using:

   .. code-block:: python

      configuredRadioCollection.find_one({"xbeeMac": xbeeMacAddress})

   If not found, a descriptive error is returned.

Deletion Steps
""""""""""""""""

Once validated, two deletion operations are performed:

1. **Delete configuration entry** from `configuredRadioCollection`:

   .. code-block:: python

      configuredRadioCollection.delete_one({"xbeeMac": xbeeMacAddress})

2. **Drop historical data** from the MAC-named collection:

   .. code-block:: python

      gatewayDb[xbeeMacAddress].drop()

   This removes the full collection associated with the XBee, including all sensor records.

Success Criteria
""""""""""""""""""

To confirm successful deletion:

- The `delete_one()` operation must indicate `deleted_count == 1`
- The dropped historian collection name must no longer appear in:

   .. code-block:: python

      gatewayDb.list_collection_names()

If both are successful:

- The reusable Modbus address pool is refreshed via `updateReusableAddress()`
- A success message is returned.

If either deletion fails or does not result in a change, an error response is returned:

.. code-block:: json

   {"error": "delete request received, but no changes were made."}

Error Handling
""""""""""""""""

The function uses a `try-except` block to capture all runtime exceptions and return a structured error message:

.. code-block:: json

   {"error": "<exception message>"}

Side Effects
""""""""""""""

- **State Mutation**: The gateway system's configuration and historical memory are permanently altered.
- **Cleanup**: Releasing unused Modbus address ranges by updating the reusable pool.

Notes
"""""""

- This function is **not reversible** — once the historical collection is dropped, the data is lost.
- Use with caution in live systems where monitoring and audit records are critical.
- This function assumes MongoDB handles renames and drops atomically in a single-node setup. In multi-node environments, ensure replication lag is considered.

Example Usage
"""""""""""""""

.. code-block:: python

   deleteXbeeDetails("0013A20040B2C3D4")

   # Result:
   # - Radio with MAC "0013A20040B2C3D4" removed from configuration.
   # - Historical sensor readings dropped from gatewayDb.


retrieveAllConfiguredRadio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   retrieveAllConfiguredRadio()

Retrieves a list of all configured XBee radios from the database, returning their stored configuration values (without MongoDB internal metadata). This is useful for management interfaces, diagnostics, or administrative dashboards.

   :returns:

       - A list of lists, where each inner list contains values for a configured XBee radio in the order retrieved from MongoDB.
       - Or, ``{"error": "<exception message>"}`` if an error occurs.

   :rtype: list or dict

Overview
""""""""""

This function performs a **read-only scan** of the `configuredRadioCollection`, which stores MAC address, Modbus start/end addresses, and node identifiers for each registered radio.

It **excludes MongoDB’s internal `_id` field** during retrieval and formats each result into a flat list of values.

The structure of each returned item is:

.. code-block:: python

   [
       "<xbeeNodeIdentifier>",
       "<xbeeMac>",
       <modbusStartAddress>,
       <modbusEndAddress>
   ]

These lists are then wrapped in a parent list representing all configured radios.

Implementation Details
""""""""""""""""""""""""

1. The function initializes an empty list:

   .. code-block:: python

      retrievedData = []

2. It performs a MongoDB `find()` query to fetch all documents from the `configuredRadioCollection`:

   .. code-block:: python

      allConfiguredData = configuredRadioCollection.find({}, {"_id": 0})

   - The empty query `{}` means “select all documents”.
   - The projection `{"_id": 0}` removes the `_id` field from results.

3. Each document is iterated and converted to a flat list of values:

   .. code-block:: python

      for data in allConfiguredData:
          currentDataList = []
          for key, value in data.items():
              currentDataList.append(value)

4. All flattened lists are collected into a final output list:

   .. code-block:: python

      retrievedData.append(currentDataList)

Return Value
""""""""""""""

If successful, returns:

.. code-block:: python

   [
       ["NODE_A", "0013A20040B2C3D4", 4001, 4020],
       ["NODE_B", "0013A20040B2C3D5", 4021, 4040],
       ...
   ]

If an exception is thrown (e.g., database connection failure), returns a dictionary:

.. code-block:: json

   {"error": "Detailed error message"}

Error Handling
""""""""""""""""

All operations are enclosed in a `try-except` block. Any exception thrown (including MongoDB errors) is caught and returned as a structured error message.

Side Effects
""""""""""""""

- **Read-Only**: This function does not modify the database.
- **Stateless**: It can be safely called multiple times without impacting system state.

Limitations
""""""""""""""

- The returned data does not preserve original dictionary keys, only the values. This could make parsing harder in some frontend systems.
- Order of keys in MongoDB documents is not guaranteed, so value order in each list may vary unless explicitly ordered.

Example Usage
"""""""""""""""

.. code-block:: python

   configuredRadios = retrieveAllConfiguredRadio()

   for radio in configuredRadios:
       print(f"MAC: {radio[1]}, Node: {radio[0]}, Start: {radio[2]}, End: {radio[3]}")


populateDbHelper
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   populateDbHelper()

Populates the system database with **10,000 randomly generated dummy XBee radio entries** for testing, debugging, or benchmarking purposes. This helper is meant for development and should **not be used in production environments** due to its data-spamming nature.

   :returns: None (Output is printed to console during execution)
   :rtype: None

Overview
""""""""""

This function generates a large number of fake XBee radios, each with:
- A random 16-character MAC address,
- A random Modbus start address between 39000 and 39999,
- A predictable node identifier in the format ``"Radio <i>"``,

It uses the existing `configureXbeeRadio()` function to register each dummy radio into the persistent `configuredRadioCollection`.

After each addition, it prints the current list of all configured radios using `retrieveAllConfiguredRadio()`.

Purpose
""""""""""

- Stress-testing MongoDB-based radio configuration storage
- Evaluating retrieval performance (`retrieveAllConfiguredRadio`)
- Simulating system behavior under large-scale configurations
- Validating UI elements like radio configuration tables or pagination

Implementation Details
""""""""""""""""""""""""

1. **Loop 10,000 Times**:

   The function generates 10,000 fake radios with the following code:

   .. code-block:: python

      for i in range(10000):

2. **Random XBee MAC Generation**:

   Each MAC is 16 characters long and consists of uppercase letters and digits:

   .. code-block:: python

      xbeeMac = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

   **Note**: This MAC format is synthetic and does not comply with real-world XBee IEEE 64-bit address formats (e.g., "0013A200...").

3. **Random Modbus Start Address**:

   Start address is chosen from the range 39000–39999:

   .. code-block:: python

      start = random.randint(39000, 39999)

   This ensures:
   - No conflict with typical operational address ranges (e.g., 4001–5000)
   - Isolation from manually added real radios

4. **Node Identifier Naming**:

   The node identifier is a fixed label `"Radio "` concatenated with the iteration index:

   .. code-block:: python

      nodeidentifier = "Radio " + str(i)

   This ensures each identifier is unique: `"Radio 0"` to `"Radio 9999"`.

5. **Configure Radio**:

   This line attempts to insert the generated radio into the system database:

   .. code-block:: python

      configureXbeeRadio(xbeeMac, start, nodeidentifier)

   The `configureXbeeRadio` function performs input validation, duplicate checks, and MongoDB persistence.

6. **Display Configuration**:

   After each insert, the updated list of configured radios is printed:

   .. code-block:: python

      print(retrieveAllConfiguredRadio())

   This can significantly slow down execution and flood the console due to the large volume of data.

Return Value
""""""""""""""

This function has no return value.

All feedback is shown through console output (`print()`), which is helpful during manual testing but inefficient for automation.

Side Effects
""""""""""""""

- Adds **10,000 documents** to the `configuredRadioCollection`.
- Generates **10,000 MongoDB collections** in `gatewayDb`, assuming `configureXbeeRadio` follows your documented logic.
- **Consumes Modbus address space** in the range 39000–39999.
- Can cause **significant slowdown** due to excessive console output and database writes.

Limitations
""""""""""""""

- Console output becomes unreadable beyond a few hundred entries.
- May result in performance bottlenecks, especially on limited hardware like Raspberry Pi.
- Can exhaust MongoDB resources (memory, disk, indexing) over time.
- Inserts are not de-duplicated; rare chance of MAC address collision despite randomness.

Recommendations
""""""""""""""""""

- Wrap the `print()` call in a debug flag or limit it (e.g., print every 1000 inserts).
- Use a shorter range during local testing (e.g., 100 radios) to avoid unintentional overload.
- Consider deleting all entries after the test using a cleanup helper.
- Replace raw `print(retrieveAllConfiguredRadio())` with summary statistics like:

   .. code-block:: python

      if i % 1000 == 0:
          print(f"Inserted {i+1} radios")

Example Output
""""""""""""""""

A single output from one iteration might look like this:

.. code-block:: python

   [
       ['Radio 0', 'AB12CD34EF56GH78', 39021, 39040],
       ...
   ]

__main__ Block Entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   if __name__ == "__main__":
       pass

Acts as the **script execution entry point** in Python. Ensures that code within this block is **only executed when the file is run directly**, and not when it is imported as a module in another script.

   :returns: None (currently no runtime behavior)
   :rtype: None

Overview
""""""""""

This conditional block is standard Python practice and serves as a safeguard to isolate code execution logic. It prevents automatic execution of logic when this script is imported elsewhere in your system (e.g., from another module or during testing).

In its current form, the block is empty (`pass`), which implies it's a **placeholder** for future startup logic, such as launching a process, running tests, or triggering a simulation loop.

Purpose
""""""""""

- Prevents unintentional side-effects when the module is imported.
- Offers a safe place to define the program’s default startup behavior.
- Commonly used for orchestrators like `startProcess()` or batch utilities like `populateDbHelper()`.

Implementation Details
""""""""""""""""""""""""

1. **Condition Evaluation**:

   The block checks whether the file is being run as the main program:

   .. code-block:: python

      if __name__ == "__main__":

2. **Empty Execution Block**:

   Uses Python’s `pass` keyword to indicate intentional non-operation:

   .. code-block:: python

      pass

   This means:
   - The script won’t perform any action unless populated.
   - It can safely be imported into test harnesses or integration tools.

Return Value
""""""""""""""

None. This block contains no logic or returnable function.

Side Effects
""""""""""""""

- Currently, there are no side effects.
- In future, logic placed here can:
  - Alter global variables
  - Launch services or daemons
  - Populate or modify the database
  - Run standalone validation scripts

Limitations
""""""""""""""

- The block is inert (`pass`) and performs no actions in its current state.
- Omitting `__main__` logic can lead to confusion when trying to run the file directly and expecting visible behavior.

Recommendations
""""""""""""""""""

- Replace `pass` with a functional call like:

   .. code-block:: python

      if __name__ == "__main__":
          startProcess()

- Use it for debug helpers during development:

   .. code-block:: python

      if __name__ == "__main__":
          populateDbHelper()

- Add comments indicating its purpose and which function(s) should be run for testing or production.

Example Usage
""""""""""""""""

.. code-block:: python

   if __name__ == "__main__":
       print("This module was run directly")
       startProcess()

This would run the gateway process only when the script is launched explicitly, not when imported into another script or service.


.. _modbus:

modbus
--------

Overview
^^^^^^^^^

The `modbus` module provides essential utilities for managing Modbus communication within the gateway system. It includes functions for converting data between formats suitable for Modbus registers, managing Modbus server contexts, and retrieving the local machine's network IP address. The module is integral for managing data exchange between Modbus slaves and handling networking concerns for Modbus servers.

Key Functionalities
"""""""""""""""""""""

1. **Float to Modbus Registers Conversion**:
   - Converts floating-point values to two 16-bit Modbus registers for use in Modbus communication.

2. **Modbus Server Context Management**:
   - Creates and manages a Modbus server context, including defining storage for multiple Modbus data types (Discrete Inputs, Coils, Holding Registers, and Input Registers).
   
3. **IP Address Retrieval**:
   - Retrieves the machine's network IP address, either from Ethernet or Wi-Fi interfaces, to facilitate network-based communication.

Imports
"""""""""

The following libraries are imported in the module:

- **psutil**: For accessing system and network interface information.
- **socket**: For network-related operations, particularly to retrieve network interface IP addresses.
- **struct**: Used for packing and unpacking binary data, especially for converting floating-point values to Modbus register format.
- **pymodbus.datastore**: Provides the necessary classes for Modbus data storage and server context management.

Purpose
"""""""""

This module supports Modbus communication by providing tools to:
- Convert real-world data (e.g., sensor readings) into Modbus-compatible formats.
- Set up a Modbus server context for managing Modbus data for multiple devices.
- Determine the local machine's IP address for network configuration.


floatToRegisters
^^^^^^^^^^^^^^^^^

.. code-block:: python

   floatToRegisters(floatValue)

Converts a **32-bit floating-point number** (Python `float`) into **two 16-bit Modbus register values** for compatibility with the Modbus protocol.

   :param float floatValue: A single precision floating-point number to convert.
   :returns: A list containing two 16-bit unsigned integers representing the input float in Modbus register format.
   :rtype: list[int]

Overview
""""""""""

The Modbus protocol operates on 16-bit registers, but modern sensor data (e.g., temperature, pressure, flow rate) is often represented as 32-bit IEEE 754 floating-point values. To store such values within a Modbus context, the float must be split into two 16-bit registers. 

This helper function provides that conversion using Python's built-in `struct` module.

Implementation Details
""""""""""""""""""""""""

1. **Pack the Float to Binary**:

   The input float is packed into a 4-byte binary format using little-endian (`<f`) encoding:

   .. code-block:: python

      binaryData = pack('<f', floatValue)

   - `<`: Little-endian byte order (least significant byte first).
   - `f`: 32-bit float.

2. **Unpack as Two Unsigned Shorts**:

   The binary data is unpacked into **two 16-bit unsigned integers**:

   .. code-block:: python

      return list(unpack('<HH', binaryData))

   This yields a list like `[low_word, high_word]` representing the float in Modbus register format.

Usage
""""""""

This function is used throughout the gateway system to convert real-valued sensor readings for Modbus compatibility. It is especially critical in `modbusPolling`, where incoming data from XBee radios is prepared for storage in Modbus registers.

Reference
"""""""""""

This function is used in the main gateway polling loop:

.. code-block:: python

   registerValues = []
   for val in sensorValues:
       registerValues.extend(floatToRegisters(val))

   registers = registerValues[:20]
   contextValue[0].setValues(3, startAddress, registers)
   contextValue[0].setValues(4, startAddress, registers)

The above logic shows that each sensor value is first passed to `floatToRegisters`, then the resulting register pairs are written to **Holding (FC3)** and **Input (FC4)** Modbus registers.

Limitations
""""""""""""""

- Only supports 32-bit `float` types. It does **not** handle double-precision floats or alternative encoding schemes.
- Assumes **little-endian** byte order, which may need adjustment for systems using big-endian Modbus encoding.
- No error handling for invalid input (e.g., non-numeric types).

Recommendations
""""""""""""""""""

- Consider adding a `registersToFloat()` reverse function for systems that require reading floats from Modbus registers.
- Use with Modbus register sets that are guaranteed to store **two consecutive 16-bit slots** per float.


contextManager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   contextManager()

Initializes and returns a **Modbus data context** that defines memory areas for **Discrete Inputs**, **Coils**, **Holding Registers**, and **Input Registers** using the `pymodbus` library.

   :returns: The initialized `ModbusSlaveContext` for slave ID 0.
   :rtype: pymodbus.datastore.ModbusSlaveContext

Overview
""""""""""

This function sets up the in-memory data model for a Modbus TCP server using `pymodbus`. It pre-allocates **1000 registers or bits** for each of the four primary Modbus data blocks:
- Discrete Inputs (read-only binary values)
- Coils (read/write binary values)
- Holding Registers (read/write 16-bit registers)
- Input Registers (read-only 16-bit registers)

The resulting context is structured in a way compatible with multi-slave Modbus networks, even though only slave ID `0` is actively used.

Implementation Details
""""""""""""""""""""""""

1. **Create the ModbusSlaveContext**:

   Initializes memory areas for all four standard Modbus types, each with 1000 default entries (set to zero):

   .. code-block:: python

      store = ModbusSlaveContext(
          di=ModbusSequentialDataBlock(0, [0]*1000),
          co=ModbusSequentialDataBlock(0, [0]*1000),
          hr=ModbusSequentialDataBlock(0, [0]*1000),
          ir=ModbusSequentialDataBlock(0, [0]*1000),
      )

2. **Create a ModbusServerContext**:

   Wraps the slave context into a server context to support multiple slaves (although only one is used here):

   .. code-block:: python

      contextAsNextedDic = ModbusServerContext(slaves={0: store, 1: store}, single=True)

   The `single=True` flag makes all operations target slave ID `0` unless explicitly overridden.

   Though despite the flag, the slave ID is still very relevant and requesting for data using wrong slave ID, won't return anything

3. **Extract the Slave Context**:

   The server context is accessed like a dictionary. Slave ID `0` is used by default:

   .. code-block:: python

      context = contextAsNextedDic[0]

   This context is what will be used to read/write Modbus data in functions like `modbusPolling`.

Usage
""""""""

The context returned by this function is passed to the Modbus TCP server and used throughout the gateway system. It allows real-time updates of Modbus registers using data received from XBee radios.

For example, in `modbusPolling`, register values are written like this:

.. code-block:: python

   contextValue[0].setValues(3, startAddress, registers)
   contextValue[0].setValues(4, startAddress, registers)

This means:
- Function code 3 (Holding Registers)
- Function code 4 (Input Registers)


getIpAddress
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   getIpAddress()

Determines and returns the current machine's **local IPv4 address**, preferring Ethernet interfaces over Wi-Fi, and falling back to a default if no valid network connection is detected.

   :returns: The selected IP address as a string.
   :rtype: str

Overview
""""""""""

This utility function inspects all active network interfaces on the machine using the `psutil` library and selects a valid IPv4 address. It does so with the following priorities:

1. **Ethernet IP address** (if available and valid).
2. **Wi-Fi IP address** (if Ethernet is unavailable).
3. **Default value** `"0.0.0.0"` if no valid IP is found.

It performs platform-independent pattern matching on interface names (supporting both English and Chinese characters) to differentiate between Ethernet and Wi-Fi adapters.

Implementation Details
""""""""""""""""""""""""

1. **Get all network interfaces**:

   Uses `psutil.net_if_addrs()` to enumerate all available network interfaces and their assigned addresses:

   .. code-block:: python

      interfaces = psutil.net_if_addrs()

2. **Define interface name patterns**:

   Maintains two lists of keywords to identify Ethernet and Wi-Fi adapters. These include common naming schemes across Windows, Linux, and macOS — even including **localized Chinese names**:

   .. code-block:: python

      ethernetPatterns = ['eth', 'en', 'ethernet', 'local area connection', '有线']
      wifiPatterns = ['wifi', 'wi-fi', 'wireless', 'wl', 'wlan', '无线', 'wi_fi']

3. **Iterate through interfaces**:

   Loops through all interfaces and their address entries, filtering only for **IPv4 addresses** (`AF_INET`) that are not **loopback** (`127.*`):

   .. code-block:: python

      if address.family == socket.AF_INET and not address.address.startswith("127."):

4. **Classify and select IP addresses**:

   - For **Ethernet** interfaces: 

     - Match name using `ethernetPatterns`
     - Skip **APIPA addresses** (i.e. `169.254.*.*` range, which indicate failed DHCP assignment)
     - Assign the first matching, valid IP to `ethernetIp`

   - For **Wi-Fi** interfaces: 

     - Match name using `wifiPatterns`
     - Assign first valid IP to `wifiIp`

   This ensures that **Ethernet is prioritized**, but Wi-Fi is used as a fallback.

5. **Return logic**:

   - If a valid Ethernet IP was found: return it and print the selection.
   - Else if a valid Wi-Fi IP was found: return it and print a fallback message.
   - Else: return a default `"0.0.0.0"` and print a warning.

   .. code-block:: python

      if ethernetIp:
         return ethernetIp
      elif wifiIp:
         return wifiIp
      else:
         return default

Console Output
""""""""""""""""

Depending on the selected result, the function prints a contextual message to the console:

- `"Ethernet IP Address: <ip>"`
- `"No Ethernet interface detected. Falling back to Wi-Fi."`
- `"Wi-Fi IP Address: <ip>"`
- `"No Ethernet or Wi-Fi network detected on this machine."`
- `"Using default address 0.0.0.0"`

These messages aid debugging during startup or troubleshooting in environments where networking may be unreliable.

Usage Scenario
""""""""""""""""

This function is commonly used at system or server initialization time to:

- Report which interface will be used for **network binding** (e.g., Modbus TCP).
- Show diagnostics or status in a GUI or terminal.
- Avoid binding services to the wrong interface.

Limitations
""""""""""""""

- Interface name pattern matching is **heuristic-based** and not foolproof — it may miss obscure naming schemes.
- Assumes **English or Chinese interface labels**. Will not work as expected if system is localized to another language without matching keywords.
- Does not support **IPv6** or multiple NIC prioritization strategies (e.g., metric-based routing).
- Only selects **one IP**, even if multiple Ethernet/Wi-Fi adapters are active.

Recommendations
""""""""""""""""""

- Extend the `ethernetPatterns` and `wifiPatterns` lists for non-standard naming in industrial or embedded platforms.
- Add support for selecting interfaces based on **gateway reachability** or **routing table priority** for more robust detection.
- Consider allowing **manual IP override** through a configuration file or environment variable in production systems.



.. _serialSelector:

serialSelector
----------------

Overview
^^^^^^^^^

The `serialSelector` module provides utility logic for detecting and selecting the appropriate USB serial port to which the XBee radio is connected. It simplifies setup by automating the process of identifying the correct USB interface based on its hardware serial number (HWID).

This module can also be run as a standalone CLI utility using a `--get` flag to print all connected serial devices and help users configure their system correctly by copying the HWID into the `variables.py` file.

Key Functionalities
"""""""""""""""""""

1. **Auto-select USB Serial Port**:
   - Detects all connected USB or COM serial devices.
   - Matches the correct port using a preconfigured serial number from the `variables` module.

2. **User Prompt Utility (CLI Mode)**:
   - When run as a standalone script with the `--get` flag, it lists all connected serial devices with their `port` and `hwid`.
   - Assists users in identifying and copying the correct hardware serial number for XBee connection setup.

3. **Error Handling**:
   - Gracefully handles user interruption (e.g., `Ctrl+C`), serial access issues, and other exceptions.

Imports
"""""""""

The module makes use of the following Python libraries and packages:

- **serial**: From `pyserial`, for enumerating and interacting with serial ports.
- **serial.tools.list_ports**: For retrieving a list of all serial ports on the system.
- **argparse**: For parsing command-line arguments in standalone mode.
- **sys**: To exit gracefully after displaying results.
- **asyncio**: Imported for potential future use, although unused in this module directly.
- **digi.xbee.devices.XBeeDevice**: Imported to support XBee device interaction (future integration).
- **functools.partial**: Imported but unused in the current module implementation.
- **variables** (local import): Contains user-defined configuration, specifically the `prefferedRadioSerialNumber`.

Usage
"""""

The module is typically used in two ways:

1. **Programmatic Access** (from other modules):

   .. code-block:: python

      from modules.serialSelector import selectUsbPort
      port = selectUsbPort()

2. **Command-Line Utility** (standalone):

   .. code-block:: shell

      python -m modules.serialSelector --get

   This prints a list of all detected USB/COM ports with their HWIDs, helping the user determine which value to set in `variables.prefferedRadioSerialNumber`.

Dependencies
"""""""""""""

- This module depends on `pyserial` and `digi-xbee`.
- It also requires a correctly defined `prefferedRadioSerialNumber` in the `variables.py` module to perform auto-selection.
- The XBee device itself is not opened or initialized here, but the port returned can be passed to `XBeeDevice` elsewhere in the application.

selectUsbPort
^^^^^^^^^^^^^

Definition
""""""""""

.. code-block:: python

    def selectUsbPort(get=False):

Description
""""""""""""""

Detects and returns the USB serial port corresponding to the preferred XBee radio device.  
It does this by scanning all available serial ports and matching them against a known hardware serial substring defined in the `variables.prefferedRadioSerialNumber`.

If the `get` argument is set to `True`, the function prints all available USB/COM ports along with their hardware IDs, helping the user identify the correct device to configure in the `variables` module. In this mode, the program exits after displaying information.

Parameters
""""""""""

- ``g`` (`bool`): Optional flag (default `False`).  
  If `True`, displays connected serial devices and exits.

Returns
""""""""

- (`str` or `None`) The matched USB port device name (e.g., `'COM3'`, `'/dev/ttyUSB0'`) if found.  
  Returns `None` if no matching port is found or if an error occurs.

Behavior
""""""""

- Uses `serial.tools.list_ports.comports()` to fetch a list of connected serial devices.
- Filters ports that include `"USB"` or `"COM"` in their names.
- If `get` is `True`, prints out all discovered serial devices and exits the program.
- Otherwise, searches for the port whose hardware ID contains the configured serial substring from `variables.prefferedRadioSerialNumber`.
- If found, returns the matching port name.
- If not found, prints guidance to the user to run the script with `--g` and update the `variables.py` file accordingly.

Exceptions Handled
""""""""""""""""""

- `KeyboardInterrupt`: Gracefully exits if the user aborts the operation.
- `serial.SerialException`: Handles issues with accessing serial ports.
- `Exception`: Catches any other unexpected error and logs it.

Example Usage
""""""""""""""

.. code-block:: python

    # Called during startup to automatically bind to the correct port
    port = selectUsbPort()
    if port:
        print(f"Using port: {port}")
    else:
        print("No valid USB port found. Check your connections and configuration.")

CLI Mode
""""""""

This function can also be triggered directly via command line:

.. code-block:: shell

    python -m modules.serialSelector --g

This prints all connected serial devices with hardware info, and helps configure the correct serial number in `variables.py`.

__main__ Execution Block
^^^^^^^^^^^^^^^^^^^^^^^^

Definition
"""""""""""

.. code-block:: python

    if __name__ == "__main__":

        parser = argparse.ArgumentParser(description="USB Port Selector Script")
        
        # Define flags
        parser.add_argument("-g", "--get", action="store_true", help="Retrieve and display the USB port with the preferred serial number.")
        
        # Parse the arguments
        args = parser.parse_args()

        selectUsbPort(get=args.get)

Description
""""""""""""

This block enables the `serialSelector` module to be run directly as a standalone script.  
It provides a command-line interface (CLI) for interacting with the USB port selection logic, especially useful for discovering connected XBee radios and retrieving their serial number information.

Behavior
""""""""

- Uses Python’s built-in `argparse` module to define a CLI interface.
- Adds a `--get` (or `-g`) flag to allow users to retrieve and display all connected USB/COM serial devices.
- After parsing command-line arguments, calls the `selectUsbPort(get=args.get)` function:

  - If `--get` is supplied, it prints detailed serial port info and exits.
  - If not, it proceeds with normal serial port selection.

Command-Line Usage
""""""""""""""""""

To retrieve connected USB serial devices and their hardware IDs:

.. code-block:: shell

    python -m modules.serialSelector --get

This is especially helpful during initial setup to determine the correct value for `variables.prefferedRadioSerialNumber`.

Typical Use Case
""""""""""""""""

This block is mainly for developer or deployment-time use when verifying or configuring the USB connection between the XBee radio and the system.

Note
""""""

In actual runtime, port selection is typically done automatically by calling `selectUsbPort()` from another module, using the configured serial number in `variables.py`.

.. _variables:

variables
------------

Overview
^^^^^^^^

The `variable` module serves as a centralized configuration and global state management file for the XBee Modbus gateway system.  
It defines constants and mutable runtime variables used across multiple modules including Modbus configuration, XBee communication, and application logic.

This module separates configuration from logic, enabling better modularity and maintainability of the system.

Global Configuration Constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **prefferedRadioSerialNumber**:  
  .. code-block:: python

      prefferedRadioSerialNumber = "SER=A10NX8UT"

  The USB serial number (typically from `hwid`) of the preferred XBee radio.  
  Used by the `serialSelector` module to automatically identify the correct serial port.

- **xbeeBaudRate**:  
  .. code-block:: python

      xbeeBaudRate = 9600

  The baud rate used for serial communication with the XBee device.

- **modbusPort**:  
  .. code-block:: python

      modbusPort = 5020

  The TCP port on which the Modbus server listens.  
  Common default is 502; this system uses 5020 to avoid conflicts and for better sandboxing.

- **validMacAddressLength**:  
  .. code-block:: python

      validMacAddressLength = 16

  Expected length of an XBee MAC address string (in hexadecimal digits).

- **validModbusAddressLength**:  
  .. code-block:: python

      validModbusAddressLength = 3

  Expected length of a valid Modbus address string (assumed to be three-digit numeric).

- **incrementalModbusAddress**:  
  .. code-block:: python

      incrementalModbusAddress = 50

  The number of Modbus register addresses allocated per XBee device.  
  Ensures each device has a dedicated, non-overlapping register block.

- **lowestRegister**:  
  .. code-block:: python

      lowestRegister = 0

  The base (minimum) address in the Modbus register space.

- **highestRegister**:  
  .. code-block:: python

      highestRegister = 1000 - incrementalModbusAddress

  The upper bound of usable Modbus registers (accounting for per-device allocation).  
  Set to avoid overflows when allocating `incrementalModbusAddress`-sized blocks.

Global Runtime Variables
^^^^^^^^^^^^^^^^^^^^^^^^

- **knownXbeeAddress**:  
  .. code-block:: python

      knownXbeeAddress = []

  A dynamically updated list of XBee MAC addresses that have been discovered or configured.  
  Used to track device presence and avoid duplicate configuration.

- **xbeeInstance**:  
  .. code-block:: python

      xbeeInstance = None

  Holds a reference to the currently connected `XBeeDevice` object.  
  Assigned during XBee initialization and used across modules to send/receive data.

- **xbeePollingTask**:  
  .. code-block:: python

      xbeePollingTask = None

  Holds a reference to the asyncio Task responsible for polling XBee radios.  
  Allows centralized task management (starting, stopping, or checking status).

- **data_callback**:  
  .. code-block:: python

      data_callback = None

  Placeholder for the asynchronous callback function used to process incoming XBee data packets.  
  This is dynamically assigned to link XBee reception with user-defined logic.

Usage Context
^^^^^^^^^^^^^

This module is imported into most other modules (such as `serialSelector`, `xbeeComm`, `modbus`, and `dbintegration`) to:

- Maintain consistency in port, baud rate, and address allocation logic.
- Access or update shared state variables like `xbeeInstance` and `knownXbeeAddress`.
- Prevent magic numbers or hard-coded strings scattered throughout the codebase.



.. _xbeeDAta:

xbeeData
------------

Overview
^^^^^^^^

The `xbeeData` module is responsible for decoding and parsing sensor payloads received from XBee radio devices, transforming raw byte data into human-readable values, and logging this information for historical storage and debugging purposes.

It serves as the bridge between raw radio transmission and structured application logic by applying decoding logic (using the Cayenne LPP format), extracting sensor values, and optionally interfacing with the database layer to store historical readings. This module helps centralize and abstract payload handling so other modules (such as the Modbus poller or analytics systems) can operate on clean, float-based sensor readings.

Key Responsibilities
"""""""""""""""""""""

- Decode XBee-transmitted sensor payloads from binary to float values using the **Cayenne Low Power Payload (LPP)** decoding format via the third-party `python_cayennelpp` package.
- Maintain consistent extraction of `value` fields from each decoded item.
- Persist decoded values to a MongoDB historian using the `storeXbeeHistoryData()` function from the `dbIntegration` module.
- Output extracted values for human-readable debugging and operational transparency.
- (Commented out) Provide an optional utility for retrieving XBee node identifiers (NI) through remote AT commands. This can be useful for device mapping, metadata tracking, or debugging physical deployments.

Usage Context
"""""""""""""""

This module is invoked by polling functions such as `modbusPolling()` in the `modbus` module. The `cayenneParse()` coroutine is used to interpret the sensor payload returned by XBee radios and convert it into a format suitable for storage and Modbus register mapping.

The output of this module is a clean list of floating-point sensor values derived from XBee data frames.

Dependencies
"""""""""""""

- `digi.xbee.devices`: For handling XBee addresses and device communication (used in the commented utility).
- `python_cayennelpp.decoder`: For decoding the payloads from Cayenne LPP format into structured sensor data.
- `datetime`: For timestamping sensor readings during storage.
- `dbIntegration`: Specifically for the `storeXbeeHistoryData()` function that handles database insertion of sensor logs.

This module provides a focused and reusable interface to interpret incoming payloads from edge XBee devices and is a core part of the Modbus-XBee gateway data pipeline.


getNodeId
^^^^^^^^^^

Definition
"""""""""""

.. function:: getNodeId(macAddress, initializedXbee)

    Attempts to retrieve the Node Identifier (NI string) of a remote XBee device using a remote AT command. This utility function is designed for debugging, diagnostics, or node identification purposes during network setup and maintenance but is currently **not used** in the active codebase.

    :param macAddress: The 64-bit MAC address of the remote XBee device.
    :type macAddress: str

    :param initializedXbee: An active and initialized `XBeeDevice` instance from the Digi XBee Python library.
    :type initializedXbee: digi.xbee.devices.XBeeDevice

    :returns: The Node Identifier (NI string) of the remote XBee device, or `"UNKNOWN"` if it cannot be retrieved.
    :rtype: str

Function Workflow
""""""""""""""""""

    1. A `RemoteXBeeDevice` instance is created using the provided MAC address and the initialized local XBee device.
    2. A remote AT command `"NI"` is issued to request the Node Identifier string from the target XBee device.
    3. If a valid response is returned and the `parameter` field is not `None`, the NI string is decoded from bytes to a UTF-8 string.
    4. If no valid response is received or an error occurs during the process, `"UNKNOWN"` is returned as a fallback.

Error Handling
""""""""""""""

    - If any exception occurs during the AT command or decoding process, it is caught and logged with an error message.
    - All failures result in a return value of `"UNKNOWN"` to maintain compatibility and prevent hard crashes.

    **Example Use Case (Hypothetical)**
    -----------------------------------

    .. code-block:: python

        nodeId = getNodeId("0013A200419717AE", xbeeInstance)
        print(f"Remote Node ID is: {nodeId}")

Usage Status
"""""""""""""

    - **Currently not in use** in the production code.
    - It may be useful in future implementations for enhanced node discovery, logging, or debugging during deployments.

Dependencies
""""""""""""

    - `digi.xbee.devices.RemoteXBeeDevice` for remote device representation.
    - `digi.xbee.devices.XBeeDevice.send_remote_at_command()` for issuing AT commands.

cayenneParse
^^^^^^^^^^^^

.. function:: async cayenneParse(xbeeMacAddress, xbeeByteData)

    Asynchronously parses and decodes a raw payload received from an XBee radio device using the Cayenne Low Power Payload (LPP) format. This function translates the raw binary data into a list of floating-point sensor values, stores them in the MongoDB historian, and prints the decoded result for logging purposes.

    This function acts as a critical link between the binary data transmitted by XBee remote nodes and the human-readable sensor values used in higher-level logic such as Modbus register updates or analytics.

    :param xbeeMacAddress: The 64-bit MAC address of the XBee device that sent the payload.
    :type xbeeMacAddress: str

    :param xbeeByteData: The raw data payload received from the XBee device as a bytes object.
    :type xbeeByteData: bytes

    :returns: A list of decoded float sensor values extracted from the Cayenne-formatted payload.
    :rtype: list[float]

Decoding Process
""""""""""""""""""

    1. The raw bytes are converted into a hex string (`hexConversion`) which is required by the Cayenne decoder.
    2. The `decode()` function from the `python_cayennelpp` package parses this hex string into a list of dictionaries, each representing a sensor reading.
    3. The function extracts only the `value` field from each dictionary item (if it exists), casts it to a float, and appends it to a result list.
    4. The resulting list is stored in a MongoDB database by calling :func:`storeXbeeHistoryData` with the MAC address, list of float values, and a timestamp.
    5. The decoded values are printed to the console for debugging or operational transparency.

Example Output
""""""""""""""

    .. code-block:: text

        List of values extracted from 0013A200419717AE byte array are: [22.4, 56.3, 1.02]

Usage Context
""""""""""""""

    This function is used in the :func:`modbusPolling()` routine (found in the `modbus` module), which receives raw data from the XBee serial interface, parses it using `cayenneParse()`, and writes the resulting floats into Modbus registers for network exposure.

Notes
""""""
    - Any sensor value that is `None` is skipped silently.
    - The decoder assumes that the payload strictly follows the Cayenne LPP format.
    - The database storage is timestamped using the current system time via `datetime.datetime.now()`.

Dependencies
"""""""""""""

    - `python_cayennelpp.decoder.decode` for Cayenne LPP decoding.
    - `storeXbeeHistoryData` from `dbIntegration` for MongoDB storage.
    - `datetime.datetime` for timestamping historical records.

.. _xbeeDummyDataTransmitter:

xbeeDummyDataTransmitter
----------------------------

Overview
^^^^^^^^^

Simulates XBee slave devices broadcasting structured sensor data via SoftwareSerial.  
Each slave sends a structured sensor message wrapped in an XBee Transmit Request frame to the master.  
Frames are sent via SoftwareSerial and printed to the Serial monitor for inspection.

This sketch is useful for simulating XBee slaves in a lab/test environment when actual hardware is limited.

Key Features
^^^^^^^^^^^^^

- Emulates 4 XBee slave devices.
- Sends structured payloads with XBee API frames.
- Uses SoftwareSerial to simulate individual slaves.
- Manually constructs and validates API frames and checksums.

Global Constants
^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    #define META_DATA_LEN 17
    #define START_DELIMITER 0x7E
    #define START_DELIMITER_OFFSET 0

XBee Address Definitions
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    uint8_t master_addr[]    = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xE8, 0x4F};
    uint8_t slave_1_addr[]   = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x5B, 0xE1, 0x07};
    uint8_t slave_2_addr[]   = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xEB, 0xCC};
    uint8_t slave_3_addr[]   = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xE3, 0xE2};
    uint8_t broadcast_addr[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF};

Simulated Messages
^^^^^^^^^^^^^^^^^^^^^

Each message is a simulated Cayenne payload, unique per slave.

.. code-block:: cpp

    uint8_t slave1_message[] = { ... };
    uint8_t slave2_message[] = { ... };
    uint8_t slave3_message[] = { ... };
    uint8_t slave4_message[] = { ... };

SoftwareSerial Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    SoftwareSerial slave1_serial(2, 3);
    SoftwareSerial slave2_serial(4, 5);
    SoftwareSerial slave3_serial(6, 7);
    SoftwareSerial slave4_serial(8, 9);

Function: setup
^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void setup() {
      pinMode(LED_BUILTIN, OUTPUT);
      Serial.begin(9600);
      slave1_serial.begin(9600);
      slave2_serial.begin(9600);
      slave3_serial.begin(9600);
      slave4_serial.begin(9600);
    }

Initializes serial ports and sets up slave communication channels.

Function: loop
^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void loop() {
      send_transmit_request(slave1_serial, broadcast_addr, slave1_message, sizeof(slave1_message));
      send_transmit_request(slave2_serial, broadcast_addr, slave2_message, sizeof(slave2_message));
      send_transmit_request(slave3_serial, broadcast_addr, slave3_message, sizeof(slave3_message));
      send_transmit_request(slave4_serial, broadcast_addr, slave4_message, sizeof(slave4_message));
      delay(1000);
    }

Sends a broadcast message from each simulated slave every second.

Function: send_transmit_request
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void send_transmit_request(SoftwareSerial serial, uint8_t dest_addr[], uint8_t message[], uint16_t message_len);

Constructs and sends a raw XBee Transmit Request API frame with:

- Frame delimiter (`0x7E`)
- Length, frame type, frame ID
- Destination address (64-bit + 16-bit)
- Broadcast radius and options
- Payload
- Checksum

The frame is printed as a HEX dump on Serial.

Function: calculateChecksum
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    uint8_t calculateChecksum(uint8_t* frame, int length);

Calculates the checksum for an XBee frame, excluding the start delimiter and length fields.

Function: receive_transmit_request (optional utility)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: cpp

    void receive_transmit_request();

Receives and prints an XBee API frame from Serial input. Currently unused in main logic.

Usage Notes
^^^^^^^^^^^^^^^^

- Ensure baud rate consistency across the system (`9600` in this case).
- `SoftwareSerial` pins must be physically separate and not shared.
- Only one `SoftwareSerial` interface can be actively listening at a time—this sketch assumes slaves are transmit-only.

