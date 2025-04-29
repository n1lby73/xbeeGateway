import psutil, socket
from struct import pack, unpack
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock

# Float to two 16-bit Modbus registers
def floatToRegisters(floatValue):
    
    binaryData = pack('<f', floatValue)
    return list(unpack('<HH', binaryData))

def contextManager():

    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0]*1000),  # Discrete Inputs
        co=ModbusSequentialDataBlock(0, [0]*1000),  # Coils
        hr=ModbusSequentialDataBlock(0, [0]*1000),  # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0]*1000),  # Input Registers
    )

    contextAsNextedDic = ModbusServerContext(slaves={0: store, 1:store}, single=True)
    context = contextAsNextedDic[0]

    return context

def getIpAddress():

    interfaces = psutil.net_if_addrs()
    ethernet_ip = None
    wifi_ip = None
    default = "0.0.0.0"

    for interfaceName, interfaceAddresses in interfaces.items():

        for address in interfaceAddresses:

            if address.family == socket.AF_INET and not address.address.startswith("127."):

                if "eth" in interfaceName.lower() or "en" in interfaceName.lower():

                    ethernet_ip = address.address

                elif "wifi" in interfaceName.lower() or "wl" in interfaceName.lower():

                    wifi_ip = address.address

    if ethernet_ip:

        print(f"Ethernet IP Address: {ethernet_ip}")
        return ethernet_ip
    
    elif wifi_ip:

        print("No Ethernet interface detected. Falling back to Wi-Fi.")
        print(f"Wi-Fi IP Address: {wifi_ip}")
        return wifi_ip
    
    else:

        print("No Ethernet or Wi-Fi network detected on this machine.")
        print(f"Using default address {default}")
        return default