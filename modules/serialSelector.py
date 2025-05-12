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

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="USB Port Selector Script")
    
    # Define flags
    parser.add_argument("-g", "--get", action="store_true", help="Retrieve and display the USB port with the preferred serial number.")
    
    # Parse the arguments
    args = parser.parse_args()

    selectUsbPort(get=args.get)