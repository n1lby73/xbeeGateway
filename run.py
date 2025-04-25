import platform
import asyncio
import importlib

baseModuleName = "osPlatform"

osModuleMap = {

    "Windows":"windows",
    "Linux":"linux"

}

# Detects platform where gateway is executed and starts up the gateway using the platform specified file
# This pattern was utilize because certain operations like selecting usb port are different
# Linux sees serial port as /dev/tty while windows sees it as COM - hence the decision

def detectOs():

    osName = platform.system()

    moduleSuffix = osModuleMap.get(osName)

    if not moduleSuffix:

        raise OSError (f"Unsupported operatin system: {osName}")
    
    moduleName = f"{baseModuleName}.{moduleSuffix}"

    try:

        mainModule = importlib.import_module(moduleName)
        asyncio.run(mainModule.main)

    except Exception as e:

        print(f"Failed to execute main for {osName}: {e}")


if __name__ == "__main__":
    detectOs()