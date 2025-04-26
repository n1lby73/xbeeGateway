import pymongo

dbclient = pymongo.MongoClient("mongodb://localhost:27017/")

mydb = dbclient["Gateway"]
mycol = mydb["radioModbusMap"]


mydict = { "xbeeMac": "123456", "modbusStartAddress": "0" }

x = mycol.insert_one(mydict)