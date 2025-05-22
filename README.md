Repository to hold Python Script for CorTU Gateway
Amplicon: Steps to Setup Gateway
First Steps
a. Connect the Radio
Connect the Amplicon to their network.
Ping the user name of the Amplicon to see the IP Address.
Use this command:

ping MININT-IH102UN

    Copy the IP Address you see on cmd.
    Paste the IP Address in task scheduler.
    Confirm if the Amplicon is polling on Mod Scanner in the (Connection).
    If data isn't polling, start the script manually in VSCode.

b. Ensure you're on the /Documents/CorTU-Gateway
Steps

i. Use cd .. (Tab). ii. Type cd CorTU-Gateway to enter the directory. iii. Check the IP Address of the Amplicon to see if it has changed using: bash ping MININT-IH102UN iv. To initialize the server, run: bash python main.py -p 502 --host "new ip" (Make sure you're in the CorTU-Gateway directory.)
Command Used in Crontab

@reboot (sleep 30; sudo /home/pi/Documents/raspberrypi_scripts/myenv/bin/python3 /home/pi/Documents/raspberrypi_scripts/main.py -l error -p 502 --host $(cat /home/pi/Documents/raspberrypi_scripts/ip_address.txt)) >> 
/home/pi/Documents/raspberrypi_scripts/log.txt 2>&1

To Activate a Virtual Environment on Windows
Open a terminal.
Use:

venv (tab)

until you get to script (forward arrow).

Document how to uttilize the service file
