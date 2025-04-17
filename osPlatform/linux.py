import sys
import time
# from xbee import XBee
from digi.xbee.devices import XBeeDevice
from modules.serialSelector import selectUsbPort
from modules.xbeeData import getNodeId
from modules.variables import xbeeBaudRate

serialPort = selectUsbPort()
baudRate = 9600


if not serialPort:

    print ("Gateway radio not connected")

    sys.exit(1)

def xbeePolling():

    try:

        xbee = XBeeDevice(serialPort, baudRate)
        xbee.open()

        def dataReceiveCallback(xbeeMessage):

            xbeeMacAddress = xbeeMessage.remote_device.get_64bit_addr()
            xbeeRemoteDevice = xbeeMessage.remote_device
            xbeeNodeIdentifier = xbeeMessage.remote_device.get_node_id()
            timestamp = xbeeMessage.timestamp
            data = xbeeMessage.data

            print("Received data from %s: %s %s" % (xbeeMacAddress, xbeeNodeIdentifier, data))

        xbee.add_data_received_callback(dataReceiveCallback)

        while True:
            # This is to make sure that the data is open and awaiting data
            time.sleep(1) 

    except Exception as e:

        print (e)

        pass

if __name__ == "__main__":
    xbeePolling()