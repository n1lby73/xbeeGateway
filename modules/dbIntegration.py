import pymongo
import datetime
from . import variables

dbclient = pymongo.MongoClient("mongodb://10.140.241.6:27017/")

gatewayDb = dbclient["Gateway"]
configuredRadioCollection = gatewayDb["configuredRadio"]
radioModbusMapCollection = gatewayDb["radioModbusMap"]

def modbusAddressPolice(startAddress):

    # Retrieve all the modbus start range from the db
    # Calculate the end range
    # check for available gaps from end to start
    # Store available range in db
    # validate that user specified address is within the available range

    pass

def dbQueryModbusStartAddress(xbeeMacAddress):

    try:

        xbeeMacAddress = str(xbeeMacAddress).upper()
        xbeeDetails = configuredRadioCollection.find_one({"xbeeMac":xbeeMacAddress})

        if xbeeDetails:

            startAddress = xbeeDetails["modbusStartAddress"]

            return startAddress
        
        else:

            return None
    
    except Exception as e:

        print (f"Fatal error with details as: {str(e)}")

        return None

def configureXbeeModbusStartAddress(xbeeMacAddress, startAddress, nodeIdentifier):

    try:

        xbeeMacAddress = str(xbeeMacAddress).upper()
        nodeIdentifier = str(nodeIdentifier).upper()

        if type(startAddress) is not int:

            return {"error": f"Pass {startAddress} as an integer"}
        
        if len(xbeeMacAddress) != variables.validMacAddressLength:

            return {"error": "Invalid mac address entered"}
        
        if len(str(startAddress)) != variables.validModbusAddressLength:

            return {"error": "Invalid modbus address"}
        
        if startAddress < variables.lowestRegister or startAddress > variables.highestRegister:

            return {"error":f"Modbus address out of range\n\nRange: 30000 - {variables.highestRegister}"}
        
        if nodeIdentifier == "":

            return {"error":"Invalid node identifier"}
        
        validateUniqueMacAddress = configuredRadioCollection.find_one({"xbeeMac":xbeeMacAddress})
        validateStartAddress = configuredRadioCollection.find_one({"modbusStartAddress":startAddress})
        validateNodeIdentifier = configuredRadioCollection.find_one({"xbeeNodeIdentifier":nodeIdentifier})

        if validateUniqueMacAddress:

            return {"error":f"Mac address already utilized by {validateUniqueMacAddress["xbeeNodeIdentifier"]}"}

        if validateStartAddress:
            
            return {"error":f"Start address already utilized by {validateStartAddress["xbeeNodeIdentifier"]}"}

        if validateNodeIdentifier:

            return {"error":f"Node identifier already utiilized by ({validateNodeIdentifier["xbeeMac"]})"}

        # Validate that specified modbus address is not in between two xbee device

        lastData = configuredRadioCollection.find_one(sort=[("_id", -1)])

        if lastData is not None:

            retrieveLastConfiguredAddress = lastData["modbusStartAddress"]

            validAvailableModbusAddress = int(retrieveLastConfiguredAddress) + variables.incrementalModbusAddress + 1

            if validAvailableModbusAddress > startAddress: # would still need to work on this to make it more robust and stay safe of memory gap

                print('selected memory map would cause adress overlapping')

                return {"error":f"next availiable start address is {validAvailableModbusAddress}"}

        endAddress = startAddress + variables.incrementalModbusAddress

        xbeeData = {"xbeeNodeIdentifier":nodeIdentifier, "xbeeMac":xbeeMacAddress, "modbusStartAddress":startAddress, "modbusEndAddress":endAddress}

        configuredXbee = configuredRadioCollection.insert_one(xbeeData)

        # Create collection with the name been the xbee mac address to hold the recived radio data and timestamp for history purpose

        xbeeHistoryEntry = gatewayDb[xbeeMacAddress]
        initializationData = {"timestamp": datetime.datetime.now(), "data":[0,0,0,0,0,0,0,0,0]}
        historian = xbeeHistoryEntry.insert_one(initializationData)

        if configuredXbee.inserted_id and historian.inserted_id:

            return {"success":"radio configured successfully"}
        
        return {"error": "Configuration request received, but no changes were made."}
    
    except Exception as e:

        return {"error":str(e)}
    
def updateXbeeDetails(oldXbeeMacAddress, jsonParameterToBeUpdated):

    validKeys = ["xbeeMac", "modbusStartAddress", "xbeeNodeIdentifier"]

    try:

        if not isinstance(jsonParameterToBeUpdated, dict):

            return {"error": "Structure of updated value is invalid. Expected a dictionary."}
        
        invalidKey = [key for key in jsonParameterToBeUpdated if key not in validKeys]

        if invalidKey:

            return {"error": f"Invalid keys found: {invalidKey}. Allowed keys: {validKeys}"}
        
        oldXbeeMacAddress = str(oldXbeeMacAddress).upper()
        
        oldMacExistence = configuredRadioCollection.find_one({"xbeeMac": oldXbeeMacAddress})

        if not oldMacExistence:

            return {"error": f"xbeeMac ({oldXbeeMacAddress}) not configured, hence not available for update."}
        
        jsonParameterToBeUpdated = {key: value.upper() if isinstance(value, str) else value for key, value in jsonParameterToBeUpdated.items()}

        for key in jsonParameterToBeUpdated:

            if key == "xbeeMac":

                newMacAddress = str(jsonParameterToBeUpdated.get("xbeeMac")).upper()

                if len(newMacAddress) != variables.validMacAddressLength:

                    return {"error": "Invalid mac address entered"}

                # Confirm that user is not sending same mac address to update

                if newMacAddress == oldXbeeMacAddress:

                    return {"error":"new mac address still same as current mac address"}

                # confirm new xbee mac not in existence

                newMacExistence = configuredRadioCollection.find_one({"xbeeMac": newMacAddress})

                if newMacExistence:

                    return {"error": "new mac address already exist"}
                
                # Update the already existing historian collection for the specified xbee mac address

                gatewayDb[oldXbeeMacAddress].rename(newMacAddress)

            if key == "modbusStartAddress":
                
                startAddress = int(jsonParameterToBeUpdated.get("modbusStartAddress"))

                if len(str(startAddress)) != variables.validModbusAddressLength:

                    return {"error": "Invalid modbus address"}
                
                if startAddress > variables.lowestRegister and startAddress > variables.highestRegister:

                    return {"error":f"Modbus address out of range\n\nRange: 30000 - {variables.highestRegister}"}
                # Validate that modbus start address would not conflict
                pass # would come back when modbus adress assigner helper function is created

            if key == "xbeeNodeIdentifier":

                nodeIdentifier = str(jsonParameterToBeUpdated.get("xbeeNodeIdentifier")).upper()

                if nodeIdentifier == "":

                    return {"error":"Invalid node identifier"}

                # Confirm that user is not sending same node identifier to update

                if nodeIdentifier == str(oldMacExistence.get("xbeeNodeIdentifier")):

                    return {"error":"new node identifier still same as current node identifier"}

                # confirm new node identifier not in existence

                newNodeIdentifierExistence = configuredRadioCollection.find_one({"xbeeNodeIdentifier": nodeIdentifier})

                if newNodeIdentifierExistence:

                    return {"error": "new node identifier already exist"}

        
        incomingUpdate = {"$set": jsonParameterToBeUpdated}

        update = configuredRadioCollection.update_one({"xbeeMac":oldXbeeMacAddress}, incomingUpdate)

        if update.modified_count:

            return {"success": "Document updated successfully."}
        
        return {"error": "Update request received, but no changes were made."}


    except Exception as e:

        return {"error": str(e)}

def storeXbeeHistoryData(xbeeMacAddress, xbeeData, xbeeDataTimestamp):
    
    try:

        xbeeMacAddress = str(xbeeMacAddress).upper()

        # Validate that mac address has been configured by checking if it exist in the general radio and modbus map collection
        
        validateMacAddress = configuredRadioCollection.find_one({"xbeeMac":xbeeMacAddress})

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

        if historian.inserted_id:

            return True

        print ("Could not update the database")    
        return None
    
    except Exception as e:

        print (f"Fatal error with details as; {str(e)}")
        return None

# Swap history for cases where two radio location was swapped
# In such scenerio, updating the xbee mac address would return an error
# Using this swap function is recommended as it also swap the history records of the two location

def swapXbeeHistoryAndMacAddress(firstXbeeMacAddress, secondXbeeMacAddress):

    try:

        firstXbeeMacAddress = str(firstXbeeMacAddress).upper()
        secondXbeeMacAddress = str(secondXbeeMacAddress).upper()

        validateFirstXbee = configuredRadioCollection.find_one({"xbeeMac": firstXbeeMacAddress})
        validateSecondXbee = configuredRadioCollection.find_one({"xbeeMac": secondXbeeMacAddress})
        
        if not validateFirstXbee:

            return {"error": f"first xbee mac address {(firstXbeeMacAddress)} not configured yet"}
        
        if not validateSecondXbee:

            return {"error": f"second xbee mac address {(secondXbeeMacAddress)} not configured yet"}

        # Carry out swapping

        gatewayDb[str(firstXbeeMacAddress)].rename(str(secondXbeeMacAddress))
        gatewayDb[str(secondXbeeMacAddress)].rename(str(firstXbeeMacAddress))

        firstXbeeUpdate = {"$set": {"xbeeMac":secondXbeeMacAddress}}
        secondXbeeUpdate = {"$set": {"xbeeMac":firstXbeeMacAddress}}

        firstUpdate = configuredRadioCollection.update_one({"xbeeMac":firstXbeeMacAddress}, firstXbeeUpdate)
        secondUpdate = configuredRadioCollection.update_one({"xbeeMac":secondXbeeMacAddress}, secondXbeeUpdate)

        if firstUpdate.modified_count and secondUpdate.modified_count:

            return {"success": "Document updated successfully."}
        
        return {"error": "Update request received, but no changes were made."}

    except Exception as e:

        return {"error": str(e)}

def deleteXbeeDetails(xbeeMacAddress):

    try:

        xbeeMacAddress = str(xbeeMacAddress).upper()

        macExistence = configuredRadioCollection.find_one({"xbeeMac": xbeeMacAddress})

        if not macExistence:

            return {"error": f"xbeeMac ({xbeeMacAddress}) not in existence."}
        
        macDetailsToDelete = {"xbeeMac":xbeeMacAddress}

        deleteXbee = configuredRadioCollection.delete_one(macDetailsToDelete)
        gatewayDb[xbeeMacAddress].drop()

        if deleteXbee.deleted_count and xbeeMacAddress not in gatewayDb.list_collection_names():

            return {"success": f"Deleted {xbeeMacAddress} and it's history data successfully."}
        
        return {"error": "delete request received, but no changes were made."}

    except Exception as e:

        return {"error": str(e)}

def retrieveAllConfiguredMacAddress():

    try:

        retrievedData = []
        allConfiguredData = configuredRadioCollection.find({},{"_id":0})

        for data in allConfiguredData:

            currentDataList = []

            for key, value in data.items():

                currentDataList.append(value)
            
            retrievedData.append(currentDataList)

        return retrievedData

    except Exception as e:

        return {"error": str(e)}
    
if __name__ == "__main__":
    pass