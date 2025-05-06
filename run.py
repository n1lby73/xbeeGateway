import asyncio
from modules import variables
from modules.main import startProcess


if __name__ == "__main__":

    try:

        asyncio.run(startProcess())

    except KeyboardInterrupt:

        print(f"\nUser cancelled operation\n")
    
    except Exception as e:

        print(f"Unknown error with info as: {e}")

    finally:

        if variables.xbeeInstance is not None and variables.xbeeInstance.is_open():

            variables.xbeeInstance.close()