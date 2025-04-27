import pymongo
import json
from . import variables

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")

gatewayDb = dbclient["Gateway"]
modbusStartAddressCollectioin = gatewayDb["radioModbusMap"]

def dbQueryModbusStartAddress(macAddress):

    try:

        xbeeDetails = modbusStartAddressCollectioin.find_one({"xbeeMac":macAddress})

        if xbeeDetails:

            startAddress = xbeeDetails["modbusStartAddress"]

            return startAddress
        
        else:

            return None
    
    except Exception as e:

        print (f"Fatal error with details as: {e}")

        return None

def configureXbeeModbusStartAddress(macAddress, startAddress, nodeIdentifier):

    try:

        validateUniqueMacAddress = modbusStartAddressCollectioin.find_one({"xbeeMac":macAddress})
        validateStartAddress = modbusStartAddressCollectioin.find_one({"modbusStartAddress":startAddress})

        if validateUniqueMacAddress or validateStartAddress:

            xbeeStartAddress = validateUniqueMacAddress["modbusStartAddress"]
            xbeeNodeId = validateUniqueMacAddress["xbeeNodeIdentifier"]

            return json.dumps({"error":f"Mac address ({macAddress}) already configured with start address as {xbeeStartAddress} and node identifier as {xbeeNodeId} "})

        # Validate that specified modbus address is not in between two xbee device

        lastData = modbusStartAddressCollectioin.find_one(sort=[("_id", -1)])
        retrieveLastConfiguredAddress = lastData["modbusStartAddress"]

        validAvailableModbusAddress = int(retrieveLastConfiguredAddress) + variables.incrementalModbusAddress

        if validAvailableModbusAddress < startAddress: # would still need to work on this to make it more robust and stay safe of memory gap

            print('selected memory map would cause adress overlapping')

            return json.dumps({"error":f"next availiable start address is {validAvailableModbusAddress}"})

        xbeeData = {"xbeeMac":macAddress, "modbusStartAddress":startAddress, "xbeeNodeIdentifier":nodeIdentifier}

        modbusStartAddressCollectioin.insert_one(xbeeData)

        return json.dumps({"success":xbeeData})
    
    except Exception as e:

        return json.dumps({"error":e})