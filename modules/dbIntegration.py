import pymongo

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")

gatewayDb = dbclient["Gateway"]
modbusStartAddressCollectioin = gatewayDb["radioModbusMap"]

def dbQueryModbusStartAddress(macAddress):

    xbeeDetails = modbusStartAddressCollectioin.find_one({"xbeeMac":macAddress})

    if xbeeDetails:

        startAddress = xbeeDetails["modbusStartAddress"]

        return startAddress
    
    else:

        return None




mydict = { "xbeeMac": "123456", "modbusStartAddress": "0" }

x = mycol.insert_one(mydict)