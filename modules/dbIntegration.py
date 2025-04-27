import pymongo
from . import variables

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")

gatewayDb = dbclient["Gateway"]
modbusStartAddressCollectioin = gatewayDb["radioModbusMap"]

def dbQueryModbusStartAddress(xbeeMacAddress):

    try:

        xbeeDetails = modbusStartAddressCollectioin.find_one({"xbeeMac":xbeeMacAddress})

        if xbeeDetails:

            startAddress = xbeeDetails["modbusStartAddress"]

            return startAddress
        
        else:

            return None
    
    except Exception as e:

        print (f"Fatal error with details as: {e}")

        return None

def configureXbeeModbusStartAddress(xbeeMacAddress, startAddress, nodeIdentifier):

    try:

        validateUniqueMacAddress = modbusStartAddressCollectioin.find_one({"xbeeMac":xbeeMacAddress})
        validateStartAddress = modbusStartAddressCollectioin.find_one({"modbusStartAddress":startAddress})

        if validateUniqueMacAddress or validateStartAddress:

            xbeeStartAddress = validateUniqueMacAddress["modbusStartAddress"]
            xbeeNodeId = validateUniqueMacAddress["xbeeNodeIdentifier"]

            return {"error":f"Mac address ({xbeeMacAddress}) already configured with start address as {xbeeStartAddress} and node identifier as {xbeeNodeId} "}

        # Validate that specified modbus address is not in between two xbee device

        lastData = modbusStartAddressCollectioin.find_one(sort=[("_id", -1)])
        retrieveLastConfiguredAddress = lastData["modbusStartAddress"]

        validAvailableModbusAddress = int(retrieveLastConfiguredAddress) + variables.incrementalModbusAddress

        if validAvailableModbusAddress < startAddress: # would still need to work on this to make it more robust and stay safe of memory gap

            print('selected memory map would cause adress overlapping')

            return {"error":f"next availiable start address is {validAvailableModbusAddress}"}

        xbeeData = {"xbeeMac":xbeeMacAddress, "modbusStartAddress":startAddress, "xbeeNodeIdentifier":nodeIdentifier}

        configuredXbee = modbusStartAddressCollectioin.insert_one(xbeeData)

        if configuredXbee.inserted_id > 0:

            return {"success":"radio configured successfully"}
        
        return {"error": "Configuration request received, but no changes were made."}
    
    except Exception as e:

        return {"error":e}
    
def updateXbeeDetails(xbeeMacAddress, jsonParameterToBeUpdated):

    validKeys = ["xbeeMac", "modbusStartAddress", "xbeeNodeIdentifier"]

    try:

        if not isinstance(jsonParameterToBeUpdated, dict):

            return {"error": "Invalid data type. Expected a dictionary."}
        
        invalidKey = [key for key in jsonParameterToBeUpdated if key not in validKeys]

        if invalidKey:

            return {"error": f"Invalid keys found: {invalidKey}. Allowed keys: {validKeys}"}
        
        macExistence = modbusStartAddressCollectioin.find_one({"xbeeMac": xbeeMacAddress})

        if not macExistence:

            return {"error": f"xbeeMac ({xbeeMacAddress}) not configured, hence not available for update."}
        
        incomingUpdate = {"$set": jsonParameterToBeUpdated}

        update = modbusStartAddressCollectioin.update_one({"xbeeMac":xbeeMacAddress}, incomingUpdate)

        if update.modified_count > 0:

            return {"success": "Document updated successfully."}
        
        return {"error": "Update request received, but no changes were made."}


    except Exception as e:

        return {"error": e}

def deleteXbeeDetails(xbeeMacAddress):

    try:

        macExistence = modbusStartAddressCollectioin.find_one({"xbeeMac": xbeeMacAddress})

        if not macExistence:

            return {"error": f"xbeeMac ({xbeeMacAddress}) not in existence."}
        
        macDetailsToDelete = {"xbeeMac":xbeeMacAddress}

        deleteXbeeDetails = modbusStartAddressCollectioin.delete_one(macDetailsToDelete)

        if deleteXbeeDetails.deleted_count > 0:

            return {"success": f"{xbeeMacAddress} deleted successfully."}
        
        return {"error": "delete request received, but no changes were made."}

    except Exception as e:

        return {"error": e}