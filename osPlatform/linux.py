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
# xbeeDataMacLock = asyncio.Lock()
serialPort = selectUsbPort()



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
            # cayenneParse(str(xbeeMacAddress), variables.xbeeDataAsByte, macIsNew)

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

    # nextModbusAddressStart = 0


    while True:

        mac, raw_data, ismac = await xbeeQueue.get()

        try:
            cayenneParse(mac, raw_data, ismac)

            for macAddress, macData in variables.xbeeMacAndDataMap.items():

                sensorValues = macData.get("sensorValues", [])

                 # Assign a block if first time
                if macAddress not in variables.xbeeAddressModbusMap:
                    variables.xbeeAddressModbusMap[macAddress] = variables.nextModbusAddressStart
                    variables.nextModbusAddressStart += 50

                # Convert floats to register values
                register_values = []
                for val in sensorValues:
                    register_values.extend(floatToRegisters(val))

                # Limit to 20 registers (10 floats)
                regs = register_values[:20]
                start_addr = variables.xbeeAddressModbusMap[macAddress]

                # Write to Holding (FC3) and Input (FC4) registers
                # contextValue.setValues(3, start_addr, regs)
                # contextValue.setValues(4, start_addr, regs)
                for i in contextValue:
                    print (i)
                slave = contextValue.getSlaveContext(0)
                slave.setValues(3, start_addr, regs)
                slave.setValues(4, start_addr, regs)

        except Exception as e:
            
            print(f"Modbus polling error: {e}")

        finally:
            xbeeQueue.task_done()
        # time.sleep(1)



async def modbusServer(context):

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'XbeeGateway'
    identity.ProductCode = 'XBEE'
    identity.VendorUrl = 'http://yourdomain.com'
    identity.ProductName = 'Modbus TCP Xbee Gateway'
    identity.ModelName = 'ModbusTCPv1'
    identity.MajorMinorRevision = '1.0'

    print("Starting Modbus TCP server on port 5020...")
    await StartAsyncTcpServer(context, identity=identity, address=("0.0.0.0", 5020))


# if __name__ == "__main__":
#     await asyncio.gather(
#         xbeePolling())

# Main entry
async def main():
    context = contextManager()
    await asyncio.gather(
        xbeePolling(),
        modbusPolling(context),
        modbusServer(context)
        # process_data(context),
    )

if __name__ == "__main__":
    asyncio.run(main())