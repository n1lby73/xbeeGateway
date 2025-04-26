import sys, asyncio
from datetime import datetime
from modules import variables
from digi.xbee.devices import XBeeDevice
from modules.xbeeData import cayenneParse
from digi.xbee.exception import XBeeException
from pymodbus.server import StartAsyncTcpServer
from modules.serialSelector import selectUsbPort, handleUsbDisconnection
from pymodbus.device import ModbusDeviceIdentification
from modules.modbus import floatToRegisters, contextManager
from modules.dbIntegration import dbQueryModbusStartAddress
# from functools import partial

# Async queue to store incoming packets
xbeeQueue = asyncio.Queue() # Stores recieved mac address and data temporarily for processing
serialPort = selectUsbPort()
variables.xbeeInstance = XBeeDevice(serialPort, variables.xbeeBaudRate)


if not serialPort:

    print ("Gateway radio not connected")

    sys.exit(1)

# Async wrapper for polling XBee data and placing into queue
async def xbeePolling():

    try:

        variables.xbeeInstance.open()

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

        variables.xbeeInstance.add_data_received_callback(dataReceiveCallback)
        # variables.xbeeInstance.add_error_callback(partial(handleUsbDisconnection, xbeeObject=variables.xbeeInstance))

        while True:
            # This is to make sure that the data is open and awaiting data
            await asyncio.sleep(1) 

    except Exception as e:

        print (e)

        pass

    finally:

        if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():

            variables.xbeeInstance.close()

async def modbusPolling(contextValue):

    while True:

        mac, raw_data, ismac = await xbeeQueue.get()

        try:

            sensorValues, xbeeMac = await cayenneParse(mac, raw_data, ismac)

            # Query database to find out start address of the retrieved mac address

            startAddress = dbQueryModbusStartAddress(xbeeMac)

            if startAddress:

                # Assign a block if first time 
                # if xbeeMac not in variables.xbeeAddressModbusMap:

                #     variables.xbeeAddressModbusMap[xbeeMac] = variables.nextModbusAddressStart
                #     variables.nextModbusAddressStart += variables.incrementalModbusAddress  # Reserve 50 registers per device

                # Convert floats to register values
                registerValues = []
                for val in sensorValues:
                    registerValues.extend(floatToRegisters(val))
                
                # Limit to 20 registers (10 floats)
                registers = registerValues[:20]
                # startAddress = variables.xbeeAddressModbusMap[xbeeMac]

                # Write to Holding (FC3) and Input (FC4) registers
                # contextValue[0][0].setValues(3, start_addr, regs)
                # contextValue[0][0].setValues(4, start_addr, regs)
                contextValue[0].setValues(3, startAddress, registers)
                contextValue[0].setValues(4, startAddress, registers)
            
            else:

                print (f"Xbee radio with mac address {xbeeMac}, has not been configured")

        except Exception as e:
            
            print(f"Modbus polling error: {e}")

        finally:

            xbeeQueue.task_done()
            await asyncio.sleep(0)

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
    variables.xbeePollingTask = asyncio.create_task(xbeePolling())

    await asyncio.gather(

        # xbeePolling(),
        variables.xbeePollingTask,
        modbusPolling(context),
        modbusServer(context)

    )

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(f"\nUser cancelled operation\n")
    
    except Exception as e:

        print(f"Unknown error with info as: {e}")

    finally:

        if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():

            variables.xbeeInstance.close()