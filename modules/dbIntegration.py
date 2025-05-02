from . import variables
from .modbus import getIpAddress
from pymongo.errors import PyMongoError
import pymongo, datetime, random, string

dbclient = pymongo.MongoClient("mongodb://"+getIpAddress()+":27017/")

gatewayDb = dbclient["Gateway"]
configuredRadioCollection = gatewayDb["configuredRadio"]
availableModbusAddressCollection = gatewayDb["availableModbusAddress"]

def modbusAddressPolice(proposedStartAddress, supposedEndAddress):

    try:

        if len(str(proposedStartAddress)) != variables.validModbusAddressLength:

            return {"error": "Invalid modbus address"}

        if proposedStartAddress < variables.lowestRegister or supposedEndAddress > variables.highestRegister+1:

            return {"error":f"Modbus address out of range\n\nRange: 30000 - {variables.highestRegister}"}
        
        # Retrieve all the modbus startAddress and endAddress range from the db

        allConfiguredAddress = list(configuredRadioCollection.find({}, {"modbusStartAddress": 1, "modbusEndAddress": 1, "_id": 0}))
        
        # Check that passed address is available for use

        for storedAddress in allConfiguredAddress:

            startAddress = storedAddress.get("modbusStartAddress")
            endAddress = storedAddress.get("modbusEndAddress")

            # validate that user specified address is within the available range

            if supposedEndAddress >= startAddress and proposedStartAddress <= endAddress:

                return {"error":'Could not update:\n\nSelected modbus startAddress address would cause adress overlapping'}
        
        return True

    except Exception as e:

        return {"error": f"{str(e)}"}       

def updateReusableAddress(returnData=None):

    try:

        availableModbusAddressCollection.drop()
        dataList = []

        # Retrieve all configured ranges and sort by startAddress address
        utiilizedRange = list(configuredRadioCollection.find({}, {"modbusStartAddress": 1, "modbusEndAddress": 1, "_id": 0}))
        utiilizedRange.sort(key=lambda x: x["modbusStartAddress"])

        # Define register bounds
        lowestPossibleAddress = variables.lowestRegister  # e.g., 30000
        highestPossibleAddress = variables.highestRegister  # e.g., 39999

        # Initialize previous endAddress to the minimum address
        previousEnd = lowestPossibleAddress - 1

        for address in utiilizedRange:

            startAddress = address["modbusStartAddress"]
            endAddress = address["modbusEndAddress"]

            # If there is a gap between previous endAddress and current startAddress
            if startAddress - previousEnd > 1:

                gapStart = previousEnd + 1
                gapEnd = startAddress - 1
                gapSize = gapEnd - gapStart + 1

                if gapSize >= variables.incrementalModbusAddress:

                    usable = "✅"

                else:

                    usable = "❌"

                availableRange = {"modbusAddressRange": f'{gapStart}-{gapEnd}', "size": gapSize, "consumable": usable}

                try:

                    availableModbusAddressCollection.insert_one(availableRange)

                    if returnData is not None:

                        dataList.append(availableRange)
                
                except PyMongoError as e:

                    return {"error":f"failed to store {availableRange} in database", "details": str(e)}

            previousEnd = max(previousEnd, endAddress)

        # Check for any remaining gap at the endAddress
        if highestPossibleAddress - previousEnd >= 1:

            gapStart = previousEnd + 1
            gapEnd = highestPossibleAddress
            gapSize = gapEnd - gapStart + 1

            if gapSize >= variables.incrementalModbusAddress:

                usable = "✅"

            else:

                usable = "❌"

            availableRange = {"modbusAddressRange": f'{gapStart}-{gapEnd}', "size": gapSize, "consumable":usable}

            try:

                availableModbusAddressCollection.insert_one(availableRange)

                if returnData is not None:

                    dataList.append(availableRange)
                
            except PyMongoError as e:

                return {"error":f'failed to store {availableRange} in database', "details": str(e)}

        if dataList and returnData is not None:

            return dataList
        
        if not dataList and returnData is not None:

            return {"info": "No available address gaps found."}
        
        if returnData is None:

            return 

    except Exception as e:

        return {"error": str(e)}

def updateAllEndAddress(newRange):

    try:

        updateOperation = []

        for doc in configuredRadioCollection.find({}, {"modbusStartAddress":1}):

            startAddress = doc.get("modbusStartAddress")

            if startAddress is not None:
                
                newEndAddress = startAddress + (newRange - 1)

                updateOperation.append(pymongo.UpdateOne({"_id":doc["_id"]}, {"$set":{"modbusEndAddress":newEndAddress}}))

        if updateOperation:

            result = configuredRadioCollection.bulk_write(updateOperation)
        
        if result.modified_count:

            updateReusableAddress()

            return {"sucess":f"updated {result.modified_count}"}
        
    except Exception as e:

        return{"error":str(e)}

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

def configureXbeeRadio(xbeeMacAddress, startAddress, nodeIdentifier):

    try:

        xbeeMacAddress = str(xbeeMacAddress).upper()
        nodeIdentifier = str(nodeIdentifier).upper()

        if type(startAddress) is not int:

            return {"error": f"Pass {startAddress} as an integer"}
        
        if len(xbeeMacAddress) != variables.validMacAddressLength:

            return {"error": "Invalid mac address entered"}

        if not nodeIdentifier.strip():

            return {"error":"Invalid node identifier"}
        
        validateUniqueMacAddress = configuredRadioCollection.find_one({"xbeeMac":xbeeMacAddress})
        validateStartAddress = configuredRadioCollection.find_one({"modbusStartAddress":startAddress})
        validateNodeIdentifier = configuredRadioCollection.find_one({"xbeeNodeIdentifier":nodeIdentifier})

        if validateUniqueMacAddress:

            return {"error":f"Mac address already utilized by {validateUniqueMacAddress['xbeeNodeIdentifier']}"}

        if validateStartAddress:
            
            return {"error":f"Start address already utilized by {validateStartAddress['xbeeNodeIdentifier']}"}

        if validateNodeIdentifier:

            return {"error":f"Node identifier already utiilized by ({validateNodeIdentifier[xbeeMac]})"}

        # Validate that specified modbus address is not in between two xbee device

        endAddress = startAddress + (variables.incrementalModbusAddress - 1)
        validAddress = modbusAddressPolice(startAddress, endAddress)

        if validAddress != True:

            return validAddress
        
        xbeeData = {"xbeeNodeIdentifier":nodeIdentifier, "xbeeMac":xbeeMacAddress, "modbusStartAddress":startAddress, "modbusEndAddress":endAddress}

        configuredXbee = configuredRadioCollection.insert_one(xbeeData)

        updateReusableAddress()

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

    validKeys = ["xbeeMac", "modbusStartAddress", "modbusEndAddress", "xbeeNodeIdentifier"]

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

            if key in ("modbusStartAddress", "modbusEndAddress"):

                # Resolve startAddress and endAddress from input or fallback
                startAddress = int(jsonParameterToBeUpdated.get("modbusStartAddress", oldMacExistence.get("modbusStartAddress")))
                endAddress = int(jsonParameterToBeUpdated.get("modbusEndAddress", oldMacExistence.get("modbusEndAddress")))

                updateNeeded = True

                validAddress = modbusAddressPolice(startAddress, endAddress)

                if validAddress != True:
                    
                    return validAddress

            # if key == "modbusStartAddress": # create one for modbus endAddress address
                
            #     startAddress = int(jsonParameterToBeUpdated.get("modbusStartAddress"))

            #     if "modbusEndAddress" in jsonParameterToBeUpdated:

            #         endAddress = jsonParameterToBeUpdated["modbusEndAddress"]
                
            #     else:

            #         endAddress = oldMacExistence["modbusEndAddress"]

            #     # Commented out the below block for cases where the user wants to edit the both address
            #     # if endAddress > startAddress:

            #     #     return {"error":"end address can't be lower than start address"}
                
            #     updateNeeded = True

            #     validAddress = modbusAddressPolice(startAddress, endAddress)

            #     if validAddress != True:

            #         return validAddress
                
            #     # Validate that modbus startAddress address would not conflict 
            #     pass # would come back when modbus adress assigner helper function is created

            # if key == "modbusEndAddress":

            #     endAddress = int(jsonParameterToBeUpdated.get("modbusEndAddress"))

            #     if "modbusStartAddress" in jsonParameterToBeUpdated:

            #         startAddress = jsonParameterToBeUpdated["modbusStartAddress"]
                
            #     else:

            #         startAddress = oldMacExistence["modbusStartAddress"]
        
            #     # Commented out the below block for cases where the user wants to edit the both address
            #     # if endAddress < startAddress:

            #     #     return {"error":"end address can't be lower than start address"}
                
            #     updateNeeded = True

            #     validAddress = modbusAddressPolice(startAddress, endAddress)

            #     if validAddress != True:

            #         return validAddress

            if key == "xbeeNodeIdentifier":

                nodeIdentifier = str(jsonParameterToBeUpdated.get("xbeeNodeIdentifier")).upper()

                if not nodeIdentifier.strip():

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

            if updateNeeded == True:

                updateReusableAddress()

                updateNeeded = False

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

            updateReusableAddress()

            return {"success": f"Deleted {xbeeMacAddress} and it's history data successfully."}
        
        return {"error": "delete request received, but no changes were made."}

    except Exception as e:

        return {"error": str(e)}

def retrieveAllConfiguredRadio():

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

def populateDbHelper():

    for i in range(10000):

        xbeeMac = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))
        start = random.randint(39000, 39999)
        # nodeidentifier = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        nodeidentifier = "Radio " + str(i)

        configureXbeeRadio(xbeeMac, start, nodeidentifier)
        print (retrieveAllConfiguredRadio())

if __name__ == "__main__":

    print(updateReusableAddress())

    pass