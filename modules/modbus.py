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

    contextAsNextedDic = ModbusServerContext(slaves={0: store, 1:store}, single=False)
    context = contextAsNextedDic[0]

    return contextAsNextedDic