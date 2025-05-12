# prefferedRadioSerialNumber = "SER=AQ016E77"
# prefferedRadioSerialNumber = "SER=AQ015ZB9"
prefferedRadioSerialNumber = "SER=A10NX8UT"
xbeeBaudRate = 9600
modbusPort = 5020
validMacAddressLength = 16
validModbusAddressLength = 3
incrementalModbusAddress = 50
lowestRegister = 0
highestRegister = 1000 - incrementalModbusAddress
# xbeeDataAsByte = None # not used
knownXbeeAddress = []
# xbeeAddressModbusMap = {} # not used
# nextModbusAddressStart = 0
# xbeeMacAndDataMap = {}
xbeeInstance = None # Holds the current xbee object instance
xbeePollingTask = None # Holds the current polling task
data_callback = None
radioFlag = None