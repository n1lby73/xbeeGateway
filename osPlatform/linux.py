from xbee import XBee
from modules.serialSelector import selectUsbPort
from modules.variables import xbeeBaudRate

serialPort = selectUsbPort()

print (serialPort)

# def xbeePolling():

#     try:

#         xbee = x

#     except: