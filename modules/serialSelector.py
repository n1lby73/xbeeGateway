import serial
import serial.tools.list_ports
from .variables import prefferedRadioSerialNumber

def selectUsbPort():
    
    try:

        ports = list(serial.tools.list_ports.comports())

        usbPorts = [{"port":port.device, "hwid":port.hwid} for port in ports if "USB" in port.device.upper()]

        if usbPorts:
            
            selectedPort = next((retrievedPort["port"] for retrievedPort in usbPorts if prefferedRadioSerialNumber in retrievedPort.get("hwid")), None)

            # for port in usbPorts:

            #     if prefferedRadioSerialNumber in port.get("hwid"):

            #         selectedPort = port["port"]
            print(f"port description is{selectedPort}")

    except:
        print ("usbPorts")
if __name__ == "__main__":
    selectUsbPort()