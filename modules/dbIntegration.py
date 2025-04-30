import pymongo
import datetime
from . import variables
from .modbus import getIpAddress

dbclient = pymongo.MongoClient("mongodb://"+getIpAddress()+":27017/")

gatewayDb = dbclient["Gateway"]
configuredRadioCollection = gatewayDb["configuredRadio"]
availableModbusAddressCollection = gatewayDb["availableModbusAddress"]

def modbusAddressPolice(proposedStartAddress, supposedEndAddress):

    try:

        if len(str(proposedStartAddress)) != variables.validModbusAddressLength:

            return {"error": "Invalid modbus address"}

        if proposedStartAddress < variables.lowestRegister or supposedEndAddress > variables.highestRegister:

            return {"error":f"Modbus address out of range\n\nRange: 30000 - {variables.highestRegister}"}
        
        # Retrieve all the modbus start and end range from the db

        allConfiguredAddress = list(configuredRadioCollection.find({}, {"modbusStartAddress": 1, "modbusEndAddress": 1, "_id": 0}))
        
        # Check that passed address is available for use
        for i in allConfiguredAddress:
            print (i)
        print ("what the hell")
        for storedAddress in allConfiguredAddress:
            print (storedAddress)
            startAddress = storedAddress.get("modbusStartAddress")
            endAddress = storedAddress.get("modbusEndAddress")

            # validate that user specified address is within the available range
            print (startAddress,endAddress)
            print (proposedStartAddress, supposedEndAddress)
            # if proposedStartAddress >= startAddress and supposedEndAddress >= endAddress:
            if supposedEndAddress >= startAddress and proposedStartAddress <= endAddress:

                return {"error":'Could not update:\n\nSelected modbus start address would cause adress overlapping'}
        
        return True

    except Exception as e:

        return {"error": f"{str(e)}"}       

# def retrieveReusableAddress():

#     allConfiguredAddress = configuredRadioCollection.find({}, {"modbusStartAddress": 1, "modbusEndAddress": 1, "_id": 0})

#     for storedAddress in allConfiguredAddress:

#         startAddress = storedAddress.get("modbusStartAddress")
#         endAddress = storedAddress.get("modbusEndAddress")



#     pass

def modbusAddressP(proposedStartAddress, gapSize=50):

    try:

        # Check the length and range of the proposed start address
        if len(str(proposedStartAddress)) != variables.validModbusAddressLength:
            return {"error": "Invalid modbus address"}

        if proposedStartAddress < variables.lowestRegister or proposedStartAddress > variables.highestRegister:
            return {"error": f"Modbus address out of range\n\nRange: {variables.lowestRegister} - {variables.highestRegister}"}

        # Retrieve all the modbus start and end range from the db
        allConfiguredAddress = configuredRadioCollection.find({}, {"modbusStartAddress": 1, "modbusEndAddress": 1, "_id": 0})
        
        address_gaps = []  # Will store valid address gaps
        
        # Check that the passed address is available for use
        for storedAddress in allConfiguredAddress:

            startAddress = storedAddress.get("modbusStartAddress")
            endAddress = storedAddress.get("modbusEndAddress")

            # Check if the proposed start address is within any of the existing address ranges
            if proposedStartAddress >= startAddress and proposedStartAddress <= endAddress:
                return {"error": 'Could not update:\n\nSelected modbus start address would cause address overlapping'}

            # Identify the gaps between the end of the previous address and the start of the next one
            address_gaps.append((startAddress, endAddress))
        
        # Now we can check if the proposed start address fits in the available gaps
        address_gaps.sort()  # Sorting to process gaps sequentially

        # Let's check the available gaps for proposed start address
        last_end = variables.lowestRegister  # starting from the lowest register
        for start, end in address_gaps:
            # Check for a valid gap of size `gapSize` between previous end and current start address
            if start - last_end >= gapSize:
                # If the gap size is enough, return this as a valid range for the start address
                if last_end + gapSize <= proposedStartAddress <= start - gapSize:
                    return True  # The proposed address fits in the gap

            last_end = end  # Update the end to the current block's end

        # Check at the end of the highest register boundary
        if variables.highestRegister - last_end >= gapSize:
            if last_end + gapSize <= proposedStartAddress <= variables.highestRegister - gapSize:
                return True

        return {"error": 'No valid gap for the proposed start address found'}
    
    except Exception as e:
        return {"error": f"{str(e)}"}


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

        endAddress = startAddress + (variables.incrementalModbusAddress - 1)
        validAddress = modbusAddressPolice(startAddress, endAddress)

        if validAddress != True:

            return validAddress
        
        print (validAddress)

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

            if key == "modbusStartAddress": # create one for modbus end address
                
                startAddress = int(jsonParameterToBeUpdated.get("modbusStartAddress"))

                endAddress = startAddress + (variables.incrementalModbusAddress - 1)
                validAddress = modbusAddressPolice(startAddress, endAddress)

                if validAddress != True:

                    return validAddress
                
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

    # print(modbusAddressPolice(50000))
    pass