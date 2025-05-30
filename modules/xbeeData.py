from digi.xbee.devices import RemoteXBeeDevice, XBee64BitAddress
from python_cayennelpp.decoder import decode
from .dbIntegration import storeXbeeHistoryData
import datetime


# def getNodeId(macAddress, initializedXbee):
#     try:
#         # Create a RemoteXBeeDevice instance
#         remote_device = RemoteXBeeDevice(initializedXbee, macAddress)

#         # Send remote AT command to get the NI (Node Identifier)
#         response = initializedXbee.send_remote_at_command(remote_device, "NI")

#         # Wait for the response
#         if response:
#             return response.parameter.decode("utf-8") if response.parameter else "UNKNOWN"

#     except Exception as e:
#         print(f"Error retrieving Node ID: {e}")

#     return "UNKNOWN"

async def cayenneParse(xbeeMacAddress,xbeeByteData):

    # Convert bytes payload to hex string
    hexConversion = xbeeByteData.hex()
    
    convertedHexValues = decode(hexConversion)

    sensorValues = []

    for item in convertedHexValues:

        value = item.get("value")  # Extract the value section from the item

        if value is not None:

            sensorValues.append(float(value))  # Add float values to the list

    storeXbeeHistoryData(str(xbeeMacAddress), sensorValues, datetime.datetime.now())

    print(f"List of values extracted from {xbeeMacAddress} byte array are: {sensorValues}\n")

    return sensorValues
