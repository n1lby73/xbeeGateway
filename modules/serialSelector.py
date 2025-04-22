import serial, argparse, sys
import serial.tools.list_ports
from .variables import prefferedRadioSerialNumber

def selectUsbPort(get=False):

    selectedPort = None

    try:

        ports = list(serial.tools.list_ports.comports())

        usbPorts = [{"port":port.device, "hwid":port.hwid} for port in ports if "USB" in port.device.upper()]

        if usbPorts:
            
            if get:

                print("serial number starts with ser\n\nAvaialbe serial devices and info are:\n")

                for connectedDevices in usbPorts:
                    print (connectedDevices)

                print ("\nCopy desired device serial number and replace in variable.py file\n")

                sys.exit(0) 
            
            # Select the first port number that matches the serial number which idealy would be only one
            selectedPort = next((retrievedPort["port"] for retrievedPort in usbPorts if prefferedRadioSerialNumber in retrievedPort.get("hwid")), None)
        
        if selectedPort:

            return selectedPort
        
        else: 

            txt = "run 'python -m modules.serialSelector -get' to retrieve connected port serial number and add replace in variable.py file"
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
    
def handleUsbDisconnection(xbee):
    
    usbDetected = False
    xbee.close()
    while not usbDetected:

        print ("here..............................")

        if selectUsbPort() is not None:

            usbDetected = True
            print ("usb connected")

    # print ("Usb disconnected")
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="USB Port Selector Script")
    
    # Define flags
    parser.add_argument("-g", "--get", action="store_true", help="Retrieve and display the USB port with the preferred serial number.")
    
    # Parse the arguments
    args = parser.parse_args()

    selectUsbPort(get=args.get)