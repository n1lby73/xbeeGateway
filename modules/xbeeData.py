# # from digi.xbee.devices import RemoteXBeeDevice, XBee64BitAddress
# # # The cortu needs to wait for sometime before switching off

# # def getNodeId(xbeeMessageObject, macAddress, initializedXbee):

# #     try:

# #         response = initializedXbee.send_remote_at_command_sync(xbeeMessageObject, "NI")
# #         node_id = response.data.decode("utf-8") if response else "UNKNOWN"

# #         remote_device = RemoteXBeeDevice(initializedXbee, macAddress)

# #         # Send remote AT command 'NI' (Node Identifier)
# #         initializedXbee.send_remote_at_command(remote_device, "NI")

# #         # Wait for the response
# #         response = initializedXbee.read_remote_at_response()
# #         if response and response.command == b'NI' and response.remote_device.get_64bit_addr() == macAddress:
# #             ni = response.parameter.decode("utf-8") if response.parameter else "UNKNOWN"

# #         # ni_response = xbee.send_remote_at_command_sync(remote_device, "NI")
# #         # node_id = ni_response.data.decode("utf-8") if ni_response.data else "UNKNOWN

# #         # return node_id
# #         return ni
# #         # try:
                    
# #         #             known_nodes[xbeeMacAddress] = node_id
# #         #         except Exception as e:
# #         #             print(f"Failed to retrieve NI for {xbeeMacAddress}: {e}")
# #         #             known_nodes[xbeeMacAddress] = "UNKNOWN"

# #         #     xbeeNodeIdentifier = known_nodes[xbeeMacAddress]
# #         #     print(f"Received data from {xbeeMacAddress} ({xbeeNodeIdentifier}): {data}")

# #         # xbee.add_data_received_callback(dataReceiveCallback)

# #         # # Create remote device instance
# #         # remoteDevice = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(REMOTE_64BIT_ADDR))

# #         # # Send remote AT command to read 'NI' (Node Identifier)
# #         # node_id = device.send_remote_at_command(remoteDevice, "NI")

# #         # # node_id is a bytearray, decode if needed
# #         # if node_id:
# #         #     print("Node Identifier:", node_id.decode('utf-8'))
# #         # else:
# #         #     print("Node Identifier not set or no response received.")

# #     except Exception as e:
# #         print(f"Error: {e}")

# #     # finally:
# #     #     if device is not None and device.is_open():
# #     #         device.close()

# from digi.xbee.devices import RemoteXBeeDevice, XBee64BitAddress

# def getNodeId(macAddress, initializedXbee):
#     try:
#         remote_device = RemoteXBeeDevice(initializedXbee, macAddress)

#         # Send remote AT command to get the NI (Node Identifier)
#         initializedXbee.send_remote_at_command(remote_device, "NI")

#         # Wait for the response
#         response = initializedXbee.read_remote_at_response()

#         if (
#             response and 
#             response.command == b'NI' and 
#             response.remote_device.get_64bit_addr() == macAddress
#         ):
#             return response.parameter.decode("utf-8") if response.parameter else "UNKNOWN"

#     except Exception as e:
#         print(f"Error retrieving Node ID: {e}")

#     return "UNKNOWN"


from digi.xbee.devices import RemoteXBeeDevice, XBee64BitAddress
from python_cayennelpp.decoder import decode
from .variables import sensorValues


def getNodeId(macAddress, initializedXbee):
    try:
        # Create a RemoteXBeeDevice instance
        remote_device = RemoteXBeeDevice(initializedXbee, macAddress)

        # Send remote AT command to get the NI (Node Identifier)
        response = initializedXbee.send_remote_at_command(remote_device, "NI")

        # Wait for the response
        if response:
            return response.parameter.decode("utf-8") if response.parameter else "UNKNOWN"

    except Exception as e:
        print(f"Error retrieving Node ID: {e}")

    return "UNKNOWN"

def cayenneParse(xbeeByteData):

    # Convert bytes payload to hex string
    hexConversion = xbeeByteData.hex()
    
    convertedHexValues = decode(hexConversion)
    
    for item in convertedHexValues:

        value = item.get("value")  # Extract the value section from the item

        if value is not None:

            try:

                sensorValues.append(float(value))  # Add float values to the list

            except ValueError: # why do you have to still append a value after a value error exception has been raised

                sensorValues.append(float(value))

    if sensorValues[7] < 0:

        fakeValue = sensorValues[7] * -1
        sensorValues[7] = fakeValue

    print("List of values extracted from the JSON file:", sensorValues)

    return sensorValues
