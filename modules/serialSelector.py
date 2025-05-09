from . import variables
from functools import partial
from datetime import datetime
from digi.xbee.devices import XBeeDevice
import serial, argparse, sys, serial.tools.list_ports

def selectUsbPort(get=False):

    selectedPort = None

    try:

        ports = list(serial.tools.list_ports.comports())

        usbPorts = [{"port":port.device, "hwid":port.hwid} for port in ports if "USB" or "COM" in port.device.upper()]

        if usbPorts:
            
            if get:

                print("serial number starts with ser\n\nAvaialbe serial devices and info are:\n")

                for connectedDevices in usbPorts:
                    print (connectedDevices)

                print ("\nCopy desired device serial number and replace in variable.py file\n")

                sys.exit(0) 
            
            # Select the first port number that matches the serial number which idealy would be only one
            selectedPort = next((retrievedPort["port"] for retrievedPort in usbPorts if variables.prefferedRadioSerialNumber in retrievedPort.get("hwid")), None)
        
        if selectedPort:

            return selectedPort
        
        else: 

            txt = "run 'python -m modules.serialSelector -g' to retrieve connected port serial number and add replace in variable.py file"
            print(txt)
            return None

    except KeyboardInterrupt:

        txt = "Operation interrupted by the user."
        print(txt)
        return None
    
    except serial.SerialException as se:

        txt = f"Serial port error: {se}"
        print(txt)
        return None
    
    except Exception as e:

        txt = f"Error while selecting serial port: {str(e)}"
        print(txt)
        return None
    
def handleUsbDisconnection(err, xbeeQueue=None,xbeeObject=None):

    usbDetected = False
    variables.radioFlag = False

    xbeeObject.close()
    def dataReceiveCallback(xbeeMessage):

            xbeeMacAddress = str(xbeeMessage.remote_device.get_64bit_addr())
            timestamp = datetime.fromtimestamp(xbeeMessage.timestamp)
            xbeeDataAsByte = xbeeMessage.data

            if str(xbeeMacAddress) not in variables.knownXbeeAddress:

                print (f"\nNew XBee Address Discovered: {xbeeMacAddress}")

                variables.knownXbeeAddress.append(str(xbeeMacAddress))

                print (f"List of addresses discovered so far are: {variables.knownXbeeAddress}\n")

            print(f"Received data from {xbeeMacAddress} are: {xbeeDataAsByte}\n")
            xbeeQueue.put_nowait((xbeeMacAddress, xbeeDataAsByte))

    while not usbDetected:

        detectPort = selectUsbPort()

        if detectPort is not None:

            usbDetected = True
            xbee = XBeeDevice(detectPort, variables.xbeeBaudRate)
            xbee.open()
            xbee.add_data_received_callback(dataReceiveCallback)
            xbee.add_error_callback(partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance))

            print (f"usb connected- {detectPort}")

def radioConnectionStatus():

    return variables.radioFlag

# # In serialSelector.py
# import asyncio
# import sys
# from functools import partial
# from digi.xbee.devices import XBeeDevice
# from digi.xbee.exception import XBeeException  # Add missing import
# from . import variables

# # Add local import for xbeePolling to avoid circular dependencies
# def import_xbee_polling():
#     from osPlatform.linux import xbeePolling  # Local import to break circular dependency
#     return xbeePolling

# async def async_reconnect():
#     """Full async reconnection sequence with proper cleanup and restart"""
#     try:
#         # 1. Cancel and await old polling task
#         if variables.xbeePollingTask:
#             variables.xbeePollingTask.cancel()
#             try:
#                 await variables.xbeePollingTask
#             except asyncio.CancelledError:
#                 print("Cancelled previous polling task")
#             finally:
#                 variables.xbeePollingTask = None

#         # 2. Close old connection
#         if variables.xbeeInstance and variables.xbeeInstance.is_open():
#             variables.xbeeInstance.close()
#             print("Closed old XBee connection")

#         # 3. Allow OS to release resources
#         await asyncio.sleep(2)

#         # 4. Detect new port with retries
#         new_port = None
#         max_retries = 5
#         for attempt in range(max_retries):
#             new_port = selectUsbPort()
#             if new_port:
#                 break
#             print(f"Port detection attempt {attempt+1}/{max_retries}")
#             await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
#         if not new_port:
#             print("Failed to detect new port after retries")
#             return

#         # 5. Create and configure new device
#         variables.xbeeInstance = XBeeDevice(new_port, variables.xbeeBaudRate)
#         variables.xbeeInstance.open()
#         print(f"New connection established on {new_port}")

#         # 6. Re-register callbacks
#         if variables.data_callback:  # Ensure this is set in main.py
#             variables.xbeeInstance.add_data_received_callback(variables.data_callback)
            
#         variables.xbeeInstance.add_error_callback(
#             partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance)
#         )

#         # 7. Restart polling task using local import
#         xbeePolling = import_xbee_polling()
#         variables.xbeePollingTask = asyncio.create_task(xbeePolling())
#         print("XBee polling restarted successfully")

#     except XBeeException as xbee_err:
#         print(f"XBee error during reconnection: {xbee_err}")
#     except Exception as gen_err:
#         print(f"Critical reconnection error: {gen_err}")
#         raise

# def handleUsbDisconnection(err, xbeeObject=None):
#     """Thread-safe disconnection handler"""
#     print(f"Disconnection detected: {err}")
    
#     try:
#         loop = asyncio.get_event_loop()
#     except RuntimeError:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
    
#     if loop.is_running():
#         loop.call_soon_threadsafe(
#             lambda: loop.create_task(async_reconnect())
#         )
#     else:
#         loop.run_until_complete(async_reconnect())

# async def async_reconnect():
#     """Handles the entire reconnection process asynchronously."""
#     try:
#         # 1. Cancel old polling task if it's running
#         if variables.xbeePollingTask:
#             variables.xbeePollingTask.cancel()
#             try:
#                 await variables.xbeePollingTask
#             except asyncio.CancelledError:
#                 print("Old polling task cancelled.")

        # # 2. Close old XBee instance
        # if variables.xbeeInstance and variables.xbeeInstance.is_open():
        #     variables.xbeeInstance.close()
        #     print("Old XBee instance closed.")

        # # 3. Allow OS to release resources
        # await asyncio.sleep(2)

        # # 4. Detect new USB port
        # new_port = selectUsbPort()
        # if not new_port:
        #     print("No new USB port detected. Retrying...")
        #     return  # Exit early and let another trigger attempt reconnection

        # # 5. Create and reopen new XBee instance
        # variables.xbeeInstance = XBeeDevice(new_port, variables.xbeeBaudRate)
        # variables.xbeeInstance.open()
        # print(f"New XBee connection established on {new_port}")

        # # 6. Register callbacks again
        # variables.xbeeInstance.add_data_received_callback(dataReceiveCallback)
        # variables.xbeeInstance.add_error_callback(partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance))

        # # 7. Restart XBee polling task
        # variables.xbeePollingTask = asyncio.create_task(xbeePolling())
        # print("XBee polling restarted.")

#     except Exception as e:
#         print(f"Reconnection failed: {str(e)}")

# def handleUsbDisconnection(err, xbeeObject=None):

#     """Schedules the async reconnection process."""
#     print("USB Disconnected. Attempting reconnection...")
#     try:

        # 1. Cancel old polling task if it's running
        # if variables.xbeePollingTask:
        #     variables.xbeePollingTask.cancel()
        #     try:
        #         await variables.xbeePollingTask
        #     except asyncio.CancelledError:
        #         print("Old polling task cancelled.")

        # loop = asyncio.get_event_loop()
        # loop.create_task(async_reconnect())
    #     loop = asyncio.get_running_loop()
    #     loop.create_task(async_reconnect()) 
    # except RuntimeError:
    #     # No running loop → just run async_reconnect directly
    #     # asyncio.run(async_reconnect())
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     loop.run_until_complete(async_reconnect())  
    #     print("not found")
    # asyncio.create_task(async_reconnect())
    # asyncio.create_task(async_reconnect())
    # Get the running event loop explicitly
    # loop = asyncio.get_event_loop()
    
    # Schedule the coroutine safely in the event loop
    # loop.call_soon_threadsafe(
    #     lambda: loop.create_task(async_reconnect())
    # )

    # if variables.xbeePollingTask:
    #     variables.xbeePollingTask.cancel()
    #     try:
    #         await variables.xbeePollingTask
    #     except asyncio.CancelledError:
    #         print("Old polling task cancelled.")

    # usbDetected = False
    # # xbeeObject.close()

    # while not usbDetected:

    #     detectPort = selectUsbPort()

    #     if detectPort is not None:

    #         usbDetected = True
    #         # xbeeObject.open(port=detectPort)
    #         xbee = XBeeDevice(detectPort, variables.xbeeBaudRate)
    #         xbee.open()
            # print ("usb connected")

    # print ("Usb disconnected")

# async def async_reconnect(old_xbee, old_port):
#     """Async coroutine to handle reconnection sequence"""
#     try:
#         # 1. Cancel old polling task
#         if variables.xbeePollingTask:
#             variables.xbeePollingTask.cancel()
#             try:
#                 await variables.xbeePollingTask
#             except asyncio.CancelledError:
#                 print("Old polling task cancelled")
                
#         # 2. Close old device
#         if old_xbee.is_open():
#             old_xbee.close()
#             print(f"Closed old connection on {old_port}")

#         # 3. Allow OS to release resources
#         await asyncio.sleep(1)

#         # 4. Detect new port
#         new_port = selectUsbPort()
#         if not new_port:
#             print("No new port detected")
#             return

#         # 5. Create and open new device
#         variables.xbeeInstance = XBeeDevice(new_port, variables.xbeeBaudRate)
#         variables.xbeeInstance.open()
#         print(f"New connection established on {new_port}")

#         # 6. Re-register callback
#         variables.xbeeInstance.add_error_callback(
#             partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance)
#         )

#         # 7. Restart polling task
#         variables.xbeePollingTask = asyncio.create_task(xbeePolling())
#         print("XBee polling restarted")

#     except Exception as e:
#         print(f"Reconnection failed: {str(e)}")

# def handleUsbDisconnection(err, xbeeObject=None):
#     """Schedules async reconnection process"""
#     if not xbeeObject:
#         return

#     # Get current port before closure
#     old_port = xbeeObject.port if hasattr(xbeeObject, 'port') else None
    
#     # Schedule async reconnect
#     asyncio.create_task(async_reconnect(xbeeObject, old_port))
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="USB Port Selector Script")
    
    # Define flags
    parser.add_argument("-g", "--get", action="store_true", help="Retrieve and display the USB port with the preferred serial number.")
    
    # Parse the arguments
    args = parser.parse_args()

    selectUsbPort(get=args.get)