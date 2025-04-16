import serial
import serial.tools.list_ports
from .variables import prefferedRadioSerialNumber

def selectUsbPort():

    selectedPort = None
    
    try:

        ports = list(serial.tools.list_ports.comports())

        usbPorts = [{"port":port.device, "hwid":port.hwid} for port in ports if "USB" in port.device.upper()]

        if usbPorts:
            
            selectedPort = next((retrievedPort["port"] for retrievedPort in usbPorts if prefferedRadioSerialNumber in retrievedPort.get("hwid")), None)
        
        if selectedPort:

            return selectedPort
        
        else: 

            txt = "run 'python -m modules.serialSelector -get' to retrieve connected port serial number and add replace in variable.py file"

    except KeyboardInterrupt:

        return None
    
    except serial.SerialException:
        return None
    
    except:
        return None
    
if __name__ == "__main__":
    selectUsbPort()