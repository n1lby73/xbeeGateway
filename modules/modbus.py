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
    ethernetIp = None
    wifiIp = None
    default = "0.0.0.0"

    # Common interface name patterns for different platforms
    ethernetPatterns = [

        'eth', 'en', 'ethernet', 
        'local area connection', '有线'

    ]
    
    wifiPatterns = [

        'wifi', 'wi-fi', 'wireless', 
        'wl', 'wlan', '无线', 'wi_fi'

    ]

    for interfaceName, interfaceAddresses in interfaces.items():

        for address in interfaceAddresses:

            if address.family == socket.AF_INET and not address.address.startswith("127."):

                if any(pattern in interfaceName.lower() for pattern in ethernetPatterns):

                    if not ethernetIp:

                        ethernetIp = address.address

                elif any(pattern in interfaceName.lower() for pattern in wifiPatterns):

                    if not wifiIp:

                        wifiIp = address.address

    if ethernetIp:

        print(f"Ethernet IP Address: {ethernetIp}")
        return ethernetIp
    
    elif wifiIp:

        print("No Ethernet interface detected. Falling back to Wi-Fi.")
        print(f"Wi-Fi IP Address: {wifiIp}")
        return wifiIp
    
    else:

        print("No Ethernet or Wi-Fi network detected on this machine.")
        print(f"Using default address {default}")
        return default