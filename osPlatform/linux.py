import sys, time
# from xbee import XBee
from datetime import datetime
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import XBeeException
from modules.serialSelector import selectUsbPort
from modules.xbeeData import cayenneParse
from modules import variables

serialPort = selectUsbPort()

if not serialPort:

    print ("Gateway radio not connected")

    sys.exit(1)

def xbeePolling():

    try:

        xbee = XBeeDevice(serialPort, variables.xbeeBaudRate)
        xbee.open()

        def dataReceiveCallback(xbeeMessage):

            xbeeMacAddress = xbeeMessage.remote_device.get_64bit_addr()
            xbeeRemoteDevice = xbeeMessage.remote_device
            # xbeeNodeIdentifier = getNodeId(xbeeRemoteDevice, xbeeMacAddress, xbee)
            timestamp = datetime.fromtimestamp(xbeeMessage.timestamp)
            variables.xbeeData = xbeeMessage.data

            if str(xbeeMacAddress) not in variables.knownXbeeAddress:

                print (f"\nNew XBee Address Discovered: {xbeeMacAddress}")

                variables.knownXbeeAddress.append(str(xbeeMacAddress))

                print (f"List of addresses discovered so far is: {variables.knownXbeeAddress}\n")

            print(f"Received data from {xbeeMacAddress} @ {timestamp}: {variables.xbeeData}\n")

        xbee.add_data_received_callback(dataReceiveCallback)

        while True:
            # This is to make sure that the data is open and awaiting data
            time.sleep(1) 

    except Exception as e:

        print (e)

        pass

    finally:

        if xbee is not None and xbee.is_open():

            xbee.close()

def modbusPolling():



if __name__ == "__main__":
    xbeePolling()