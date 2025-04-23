import sys, time, asyncio
# from xbee import XBee
from datetime import datetime
from digi.xbee.devices import XBeeDevice
from digi.xbee.exception import XBeeException
from modules.serialSelector import selectUsbPort
from modules.xbeeData import cayenneParse
from modules.modbus import floatToRegisters, contextManager
from modules import variables
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification

# Async queue to store incoming packets
xbeeQueue = asyncio.Queue() # Stores recieved mac address and data temporarily for processing
xbeeMacDataQueue = asyncio.Queue()
# xbeeDataMacLock = asyncio.Lock()
serialPort = selectUsbPort()
xbee = XBeeDevice(serialPort, variables.xbeeBaudRate)



if not serialPort:

    print ("Gateway radio not connected")

    sys.exit(1)

# Async wrapper for polling XBee data and placing into queue
async def xbeePolling():

    try:

        xbee = XBeeDevice(serialPort, variables.xbeeBaudRate)
        xbee.open()

        def dataReceiveCallback(xbeeMessage):

            xbeeMacAddress = str(xbeeMessage.remote_device.get_64bit_addr())
            timestamp = datetime.fromtimestamp(xbeeMessage.timestamp)
            xbeeDataAsByte = xbeeMessage.data
            macIsNew = 0 # This value is used to denote if it's a newly found mac address so that cayenne parse would not need to query the xbeeMacAndDataMap before knowing if it's to update data or insert a new value

            if str(xbeeMacAddress) not in variables.knownXbeeAddress:

                print (f"\nNew XBee Address Discovered: {xbeeMacAddress}")

                variables.knownXbeeAddress.append(str(xbeeMacAddress))
                macIsNew = 1

                print (f"List of addresses discovered so far are: {variables.knownXbeeAddress}\n")

            print(f"Received data from {xbeeMacAddress} @ {timestamp} are: {xbeeDataAsByte}\n")
            xbeeQueue.put_nowait((xbeeMacAddress, xbeeDataAsByte, macIsNew))

        xbee.add_data_received_callback(dataReceiveCallback)

        while True:
            # This is to make sure that the data is open and awaiting data
            await asyncio.sleep(1) 

    except Exception as e:

        print (e)

        pass

    finally:

        if xbee is not None and xbee.is_open():

            xbee.close()

async def modbusPolling(contextValue):

    while True:

        mac, raw_data, ismac = await xbeeQueue.get()

        try:

            sensorValues, xbeeMac = await cayenneParse(mac, raw_data, ismac)

            # Assign a block if first time 
            if xbeeMac not in variables.xbeeAddressModbusMap:

                variables.xbeeAddressModbusMap[xbeeMac] = variables.nextModbusAddressStart
                variables.nextModbusAddressStart += 50  # Reserve 50 registers per device

            # Convert floats to register values
            register_values = []
            for val in sensorValues:
                register_values.extend(floatToRegisters(val))
            
            # Limit to 20 registers (10 floats)
            regs = register_values[:20]
            start_addr = variables.xbeeAddressModbusMap[xbeeMac]

            # Write to Holding (FC3) and Input (FC4) registers
            # contextValue[0][0].setValues(3, start_addr, regs)
            # contextValue[0][0].setValues(4, start_addr, regs)
            contextValue[0].setValues(3, start_addr, regs)
            contextValue[0].setValues(4, start_addr, regs)

        except Exception as e:
            
            print(f"Modbus polling error: {e}")

        finally:
            xbeeQueue.task_done()
            await asyncio.sleep(0)
        # time.sleep(1)



async def modbusServer(context):

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Cors System'
    identity.ProductCode = 'CSG'
    identity.VendorUrl = 'https://corssystem.com'
    identity.ProductName = 'Core Terminal Unit Gateway'
    identity.ModelName = 'Genesis'
    identity.MajorMinorRevision = '2.0'

    # unpackedContext = context[0]
    print("Starting Modbus TCP server on port 5020...")
    await StartAsyncTcpServer(context, identity=identity, address=("0.0.0.0", 5020))
    # await StartAsyncTcpServer(unpackedContext, identity=identity, address=("0.0.0.0", 5020))


# Main entry
async def main():
    context = contextManager()

    await asyncio.gather(

        xbeePolling(),
        modbusPolling(context),
        modbusServer(context)

    )

if __name__ == "__main__":
    asyncio.run(main())