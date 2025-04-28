import pymongo
import datetime
from . import variables

dbclient = pymongo.MongoClient("mongodb://10.140.241.6:27017/")

gatewayDb = dbclient["Gateway"]
radioModbusMapCollection = gatewayDb["radioModbusMap"]

def dbQueryModbusStartAddress(xbeeMacAddress):

    try:

        xbeeDetails = radioModbusMapCollection.find_one({"xbeeMac":xbeeMacAddress})

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

        if type(startAddress) is not int:

            return {"error": f"Pass {startAddress} as an integer"}
        
        validateUniqueMacAddress = radioModbusMapCollection.find_one({"xbeeMac":xbeeMacAddress})
        validateStartAddress = radioModbusMapCollection.find_one({"modbusStartAddress":startAddress})

        if validateUniqueMacAddress or validateStartAddress:

            xbeeStartAddress = validateUniqueMacAddress["modbusStartAddress"]
            xbeeNodeId = validateUniqueMacAddress["xbeeNodeIdentifier"]

            return {"error":f"Mac address ({xbeeMacAddress}) already configured with start address as {xbeeStartAddress} and node identifier as {xbeeNodeId} "}

        # Validate that specified modbus address is not in between two xbee device

        lastData = radioModbusMapCollection.find_one(sort=[("_id", -1)])

        if lastData is not None:

            retrieveLastConfiguredAddress = lastData["modbusStartAddress"]

            validAvailableModbusAddress = int(retrieveLastConfiguredAddress) + variables.incrementalModbusAddress

            if validAvailableModbusAddress < startAddress: # would still need to work on this to make it more robust and stay safe of memory gap

                print('selected memory map would cause adress overlapping')

                return {"error":f"next availiable start address is {validAvailableModbusAddress}"}

        xbeeData = {"xbeeMac":xbeeMacAddress, "modbusStartAddress":startAddress, "xbeeNodeIdentifier":nodeIdentifier}

        configuredXbee = radioModbusMapCollection.insert_one(xbeeData)

        # Create collection with the name been the xbee mac address to hold the recived radio data and timestamp for history purpose

        xbeeHistoryEntry = gatewayDb[xbeeMacAddress]
        initializationData = {"timestamp": datetime.datetime.now(), "data":"[0,0,0,0,0,0,0,0,0]"}
        historian = xbeeHistoryEntry.insert_one(initializationData)

        if configuredXbee.inserted_id > 0 and historian.inserted_id > 0:

            return {"success":"radio configured successfully"}
        
        return {"error": "Configuration request received, but no changes were made."}
    
    except Exception as e:

        return {"error":e}
    
def updateXbeeDetails(oldXbeeMacAddress, jsonParameterToBeUpdated):

    validKeys = ["xbeeMac", "modbusStartAddress", "xbeeNodeIdentifier"]

    try:

        if not isinstance(jsonParameterToBeUpdated, dict):

            return {"error": "Structure of updated value is invalid. Expected a dictionary."}
        
        invalidKey = [key for key in jsonParameterToBeUpdated if key not in validKeys]

        if invalidKey:

            return {"error": f"Invalid keys found: {invalidKey}. Allowed keys: {validKeys}"}
        
        oldMacExistence = radioModbusMapCollection.find_one({"xbeeMac": oldXbeeMacAddress})

        if not oldMacExistence:

            return {"error": f"xbeeMac ({oldXbeeMacAddress}) not configured, hence not available for update."}
        
        for key in jsonParameterToBeUpdated:

            if key == "xbeeMac":

                # Confirm that user is not sending same mac address to update

                if str(jsonParameterToBeUpdated.get("xbeeMac")) == str(oldXbeeMacAddress):

                    return {"error":"new mac address still same as current mac address"}

                # confirm new xbee mac not in existence

                newMacExistence = radioModbusMapCollection.find_one({"xbeeMac": jsonParameterToBeUpdated.get("xbeeMac")})

                if newMacExistence:

                    return {"error": "new mac address already exist"}
                
                # Update the already existing historian collection for the specified xbee mac address

                gatewayDb[oldXbeeMacAddress].rename(str(jsonParameterToBeUpdated.get("xbeeMac")))

            if key == "modbusStartAddress":
                
                # Validate that modbus start address would not conflict
                pass # would come back when modbus adress assigner helper function is created

            if key == "xbeeNodeIdentefier":

                # Confirm that user is not sending same node identifier to update

                if str(jsonParameterToBeUpdated.get("xbeeNodeIdentifier")) == str(oldMacExistence.get("xbeeNodeIdentifier")):

                    return {"error":"new node identifier still same as current node identifier"}

                # confirm new node identifier not in existence

                newNodeIdentifierExistence = radioModbusMapCollection.find_one({"xbeeNodeIdentifier": jsonParameterToBeUpdated.get("xbeeNodeIdentifier")})

                if newNodeIdentifierExistence:

                    return {"error": "new node identifier already exist"}

        
        incomingUpdate = {"$set": jsonParameterToBeUpdated}

        update = radioModbusMapCollection.update_one({"xbeeMac":oldXbeeMacAddress}, incomingUpdate)

        if update.modified_count > 0:

            return {"success": "Document updated successfully."}
        
        return {"error": "Update request received, but no changes were made."}


    except Exception as e:

        return {"error": e}

def storeXbeeHistoryData(xbeeMacAddress, xbeeData, xbeeDataTimestamp):
    
    try:

        # Validate that mac address has been configured by checking if it exist in the general radio and modbus map collection
        
        validateMacAddress = radioModbusMapCollection.find_one({"xbeeMac":xbeeMacAddress})

        if not validateMacAddress:
            
            print ("Mac Address has not been configured")
            return None
        
        # Validate that data is a list object

        if not isinstance(xbeeData, list):

            print (f"Expected data {xbeeData} should be passed as list")
            return None
        
        dataToInsert = {"timestamp": xbeeDataTimestamp, "data":xbeeData}
        xbeeHistoryEntry = gatewayDb[xbeeMacAddress]
        historian = xbeeHistoryEntry.insert_one(dataToInsert)

        if historian > 0:

            return True

        print ("Could not update the database")    
        return None
    
    except Exception as e:

        print (f"Fatal error with details as; {e}")
        return None

# Swap history for cases where two radio location was swapped
# In such scenerio, updating the xbee mac address would return an error
# Using this swap function is recommended as it also swap the history records of the two location

def swapXbeeHistoryAndMacAddress(firstXbeeMacAddress, secondXbeeMacAddress):

    try:

        validateFirstXbee = radioModbusMapCollection.find_one({"xbeeMac": firstXbeeMacAddress})
        validateSecondXbee = radioModbusMapCollection.find_one({"xbeeMac": secondXbeeMacAddress})
        
        if not validateFirstXbee:

            return {"error": f"first xbee mac address {(firstXbeeMacAddress)} not configured yet"}
        
        if not validateSecondXbee:

            return {"error": f"second xbee mac address {(secondXbeeMacAddress)} not configured yet"}

        # Carry out swapping

        gatewayDb[str(firstXbeeMacAddress)].rename(str(secondXbeeMacAddress))
        gatewayDb[str(secondXbeeMacAddress)].rename(str(firstXbeeMacAddress))

        firstXbeeUpdate = {"$set": {"xbeeMac":secondXbeeMacAddress}}
        secondXbeeUpdate = {"$set": {"xbeeMac":firstXbeeMacAddress}}

        firstUpdate = radioModbusMapCollection.update_one({"xbeeMac":firstXbeeMacAddress}, firstXbeeUpdate)
        secondUpdate = radioModbusMapCollection.update_one({"xbeeMac":secondXbeeMacAddress}, secondXbeeUpdate)

        if firstUpdate.modified_count > 0 and secondUpdate.modified_count > 0:

            return {"success": "Document updated successfully."}
        
        return {"error": "Update request received, but no changes were made."}

    except Exception as e:

        return {"error": str(e)}

def deleteXbeeDetails(xbeeMacAddress):

    try:

        macExistence = radioModbusMapCollection.find_one({"xbeeMac": xbeeMacAddress})

        if not macExistence:

            return {"error": f"xbeeMac ({xbeeMacAddress}) not in existence."}
        
        macDetailsToDelete = {"xbeeMac":xbeeMacAddress}

        deleteXbee = radioModbusMapCollection.delete_one(macDetailsToDelete)
        gatewayDb[xbeeMacAddress].drop()

        if deleteXbee.deleted_count > 0 and xbeeMacAddress not in gatewayDb.list_collection_names():

            return {"success": f"Deleted {xbeeMacAddress} and it's history data successfully."}
        
        return {"error": "delete request received, but no changes were made."}

    except Exception as e:

        return {"error": e}

def retrieveAllConfiguredMacAddress():

    try:

        retrievedData = []
        allConfiguredData = radioModbusMapCollection.find({},{"_id":0})

        for data in allConfiguredData:

            currentDataList = []

            for key, value in data.items():

                currentDataList.append(value)
            
            retrievedData.append(currentDataList)

    except Exception as e:

        return {"error": str(e)}
    
if __name__ == "__main__":
    pass