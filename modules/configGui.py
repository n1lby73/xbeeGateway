import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
from .modbus import getIpAddress
from .dbIntegration import configureXbeeRadio, retrieveAllConfiguredRadio, deleteXbeeDetails, updateXbeeDetails, updateReusableAddress, updateAllEndAddress
from .serialSelector import getListOfConnectedSerialDevice, radioConnectionStatus

class Modbus_GUI(tk.Tk):

    def __init__(self):

        super().__init__()
        self.title("Gateway GUI")
        self.geometry("800x650")

        self.head = tk.Label(self, text="CORS GATEWAY CONFIGURATION", font=("Arial", 20, "bold"))
        self.head.pack(pady=10)

        self.head_frame = tk.Frame(self)
        self.head_frame.pack(pady=10)

        self.ip_address = getIpAddress()
        self.ip_address_label = tk.Label(self.head_frame, text="Modbus Server Running At: " + self.ip_address)
        self.ip_address_label.grid(row=0, column=1, padx=10 , pady = 5)

        self.config_button = tk.Button(self.head_frame, text="Configure Serial Port", bg="blue", fg="white", command = self.configure_button)
        self.config_button.grid(row=0, column=2, padx=20 , pady = 5)

        self.connection = tk.Button(self.head_frame, text="Connection Status", bg="blue", fg="white", command = self.connection_status)
        self.connection.grid(row=0, column=3, padx=20 , pady = 5)

        self.select_usb = tk.Button(self.head_frame, text="Connected USB", bg="blue", fg="white", command = self.select_usb)
        self.select_usb.grid(row=0, column=4, padx=20 , pady = 5)

        self.canvas = tk.Canvas(self, width=800, height=8)
        self.canvas.pack()

        self.canvas.create_line(0, 3, 800, 3, fill="#D3D3D3")
        

        self.add_entry_frame = tk.Frame(self)
        self.add_entry_frame.pack(expand= True, fill="both", anchor = "center")

        self.add_label = tk.Label(self.add_entry_frame, text="Add New Entry")
        self.add_label.grid(row =0, column= 0,columnspan=3)

        self.node_identifier_label = tk.Label(self.add_entry_frame, text="Node Identifier: ", width=40)
        self.node_identifier_label.grid(row=1, column=0, padx=10, pady=10, sticky='w')
        self.node_identifier_input = tk.Entry(self.add_entry_frame, width=50)
        self.node_identifier_input.grid(row=1, column=1, pady=10, sticky='w')

        self.radio_address_label = tk.Label(self.add_entry_frame, text="Radio MAC Address: ", width=40)
        self.radio_address_label.grid(row=2, column=0,padx=10, pady=10, sticky='w')
        self.radio_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.radio_address_input.grid(row=2, column=1, pady=10, sticky='w')
        

        self.modbus_address_label = tk.Label(self.add_entry_frame, text="Modbus Start Address: ", width=40)
        self.modbus_address_label.grid(row=3, column=0, padx=10, pady=10, sticky='w')
        self.modbus_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.modbus_address_input.grid(row=3, column=1, pady=10, sticky='w')

        self.available_address = tk.Button(self.add_entry_frame, text="Available Addresses", bg = "#FFA500", fg="white", command=self.get_available_address)
        self.available_address.grid(row=3, column=2, padx=10, pady=10, sticky='w')
    

        self.button = tk.Button(self, text="Add to Database", padx=20, pady=10,bg="blue", fg="white", command=self.add_database)
        self.button.pack(pady=10)


        #Let's talk database here
        self.show_entry_frame = ttk.LabelFrame(self, border=1, text="Configured Xbee Radios", padding=5)
        self.show_entry_frame.pack(fill="both")

        self.search_frame = tk.Frame(self.show_entry_frame)
        self.search_frame.pack()

        self.search_bar = tk.Entry(self.search_frame, width=50, font=("TkDefaultFont", 12))
        self.search_bar.insert(0, "Search here")
        self.search_bar.config(fg="grey")
        self.search_bar.grid(row=0, column=0,  sticky='w')
        
        self.search_bar.bind("<FocusIn>", self.clear_placeholder)
        self.search_bar.bind("<FocusOut>", self.add_placeholder)
        self.search_bar.bind("<KeyRelease>", self.live_search)
        self.search_bar.bind("<Return>", self.live_search)

        # self.find_button = tk.Button(self.search_frame, text="Find", padx=20, bg="blue", fg="white", command=self.live_search)
        # self.find_button.grid(row=0, column=1, padx=10, pady=10)

        refresh_image_path = "modules/guiModules/refresh.png"
        refresh_image = Image.open(refresh_image_path)
        refresh_image = refresh_image.resize((20, 20), Image.LANCZOS)
        refresh_image = ImageTk.PhotoImage(refresh_image)
        self.refresh_image = refresh_image

        self.refresh_button = tk.Button(self.search_frame, image=self.refresh_image, bg= "#FFA500", command = self.refresh)
        self.refresh_button.grid(row=0, column=2, padx=10, pady=10, sticky='e')


        self.dropdown_options = ["First Modified", "Last Modified", "Ascending Modbus Address", "Descending Modbus Address"]
        self.selected_option = tk.StringVar()
        self.selected_option.set(self.dropdown_options[0])
        self.dropdown = ttk.Combobox(self.search_frame, textvariable=self.selected_option, values=self.dropdown_options, state="readonly", width=15)
        self.dropdown.grid(row=0, column=3, padx=10, pady=10, sticky='w')
        self.dropdown.bind("<<ComboboxSelected>>", self.sort_table)

        self.scroll_bar = ttk.Scrollbar(self.show_entry_frame, orient="vertical")
        self.scroll_bar.pack(side='right', fill='y')

        self.tree = ttk.Treeview(self.show_entry_frame, yscrollcommand=self.scroll_bar.set, selectmode="extended",height = 8)
        
        self.scroll_bar.config(command=self.tree.yview)

        # Define columns
        self.tree['columns'] = ('S/N',"Node Identifier", 'RadioMACAddress','ModbusAddress',  "ModbusEndAddress" )

        # Format columns
        self.tree.column("#0", width=0, stretch=tk.NO)  # Hide first empty column
        
        self.tree.column("S/N", anchor=tk.CENTER, width=30)
        self.tree.column("Node Identifier", anchor=tk.CENTER, width=180)
        self.tree.column("RadioMACAddress", anchor=tk.CENTER, width=200)
        self.tree.column("ModbusAddress", anchor=tk.CENTER, width=150)
        self.tree.column("ModbusEndAddress", anchor=tk.CENTER, width=200)


        self.tree.heading("S/N", text="S/N")
        self.tree.heading("Node Identifier", text="Node Identifier")
        self.tree.heading("RadioMACAddress", text="Radio MAC Address")
        self.tree.heading("ModbusAddress", text="Modbus Start Address")
        self.tree.heading("ModbusEndAddress", text="Modbus End Address")

        self.tree.pack()

        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=10)

        self.button = tk.Button(self.button_frame, text = "Delete Selected", padx=20, pady=10,bg="blue", fg="white", command=self.delete_selected)
        self.button.pack(side=tk.LEFT)

        self.update_button = tk.Button(self.button_frame, text = "Update Selected", padx=20, pady=10,bg="blue", fg="white", state = "normal", command=self.update_selected)
        self.update_button.pack(padx=30)

        self.available_addresses = updateReusableAddress(returnData=True) # Get available addresses from the db integration, returns it as a dictionary
        

        self.get_database()

        self.data = []

        for iid in self.tree.get_children():
            item = self.tree.item(iid)["values"]
            self.data.append((item, iid))

    
    def get_database(self):

        result = retrieveAllConfiguredRadio()

        for index, item in enumerate(result, start=1):

            self.tree.insert("", "end", text= index, values=(index, item[0], item[1], item[2], item[3]))

        if isinstance(result, dict) and result.get("error") != None: 
                    
            messagebox.showerror(title="Error", message= str(result.get("error")))


    def add_database(self):

        self.radio_address = self.radio_address_input.get()
        self.modbus_address = self.modbus_address_input.get()
        self.node_identifier = self.node_identifier_input.get()

        try:

            result = configureXbeeRadio(self.radio_address, int(self.modbus_address), self.node_identifier)

            if result.get("error") == None:

                self.radio_address_input.delete(0, tk.END)
                self.modbus_address_input.delete(0, tk.END) 
                self.node_identifier_input.delete(0, tk.END)

                messagebox.showinfo(title="Success", message="Entry added successfully.")
                self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
                self.get_database()  # Repopulate the treeview with updated data

            else:

                messagebox.showerror(title="Error", message= str(result.get("error")))

        except ValueError:

            messagebox.showerror(title="Invalid Input", message= "Please enter a valid Modbus Start Address (integer).")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
        self.get_database() 
        self.ip_address = getIpAddress()
        self.ip_address_label.config(text="Modbus Server Running At: " + self.ip_address)  # Update the IP address label
        

    def clear_placeholder(self, event):

        if self.search_bar.get() == "Search here":
            self.search_bar.delete(0, tk.END)
            self.search_bar.config(fg="black")
    
    def add_placeholder(self, event):        
        
        if self.search_bar.get() == "":
            self.search_bar.insert(0, "Search here")
            self.search_bar.config(fg="grey")

    def live_search(self, event=None):
        self.match = False
        self.search = self.search_bar.get().lower()

        for iid in self.tree.get_children():
            self.tree.detach(iid)

        for values, iid in self.data:
            if any(self.search in str(value).lower() for value in values):
                self.tree.reattach(iid, "", "end")
                self.match = True

        if not self.match:
            messagebox.showinfo(title="No Match", message="No match found.")      
                
        
    def sort_table(self, event=None):
        selection = self.dropdown.get()

        self.sort_data = []

        for iid in self.tree.get_children():
            values = self.tree.item(iid)["values"]
            sort_id = self.tree.item(iid)["text"]
            self.sort_data.append((values, iid, sort_id))

        if selection == "First Modified":
            self.sort_data.sort(key=lambda x: x[2], reverse=False)

        if selection == "Last Modified":
            self.sort_data.sort(key=lambda x: x[2], reverse=True)

        if selection == "Ascending Modbus Address":
            self.sort_data.sort(key=lambda x: x[0][3], reverse=False)
        
        if selection == "Descending Modbus Address":
            self.sort_data.sort(key=lambda x: x[0][3], reverse=True)

        for index, (values, iid, _) in enumerate(self.sort_data):
            values[0] = index + 1  # Reassign serial number
            self.tree.item(iid, values=values)
            self.tree.move(iid, "", index)


    def get_available_address(self):   
        self.available_address_window = tk.Toplevel(self)
        self.available_address_window.title("Available Addresses")
        self.available_address_window.geometry("800x300")
    
        self.available_addresses = updateReusableAddress("test")

        self.available_window = tk.Frame(self.available_address_window, padx=20, pady=20)
        self.available_window.pack(fill="both")
        
        self.scroll_bar_available = ttk.Scrollbar(self.available_window, orient="vertical")
        self.scroll_bar_available.pack(side='right', fill='y')

        self.tree_available = ttk.Treeview(self.available_window, yscrollcommand=self.scroll_bar_available.set, selectmode="extended")

        self.scroll_bar_available.config(command=self.tree_available.yview)

        # Define columns
        self.tree_available['columns'] = ('S/N',"Available Range", 'Range Size','Usuability')

        # Format columns
        self.tree_available.column("#0", width=0, stretch=tk.NO)  # Hide first empty column
        
        self.tree_available.column("S/N", anchor=tk.CENTER, width=30)
        self.tree_available.column("Available Range", anchor=tk.CENTER, width=250)
        self.tree_available.column('Range Size', anchor=tk.CENTER, width=250)
        self.tree_available.column('Usuability', anchor=tk.CENTER, width=200)


        self.tree_available.heading("S/N", text="S/N")
        self.tree_available.heading("Available Range", text="Available Range")
        self.tree_available.heading("Range Size", text="Range Size")
        self.tree_available.heading("Usuability", text="Usuability")
        
        self.tree_available.pack()


        for index, item in enumerate(self.available_addresses, start=1):
            
            self.tree_available.insert("", "end", text= index, values=(index, item["modbusAddressRange"], item["size"], item["consumable"]))

        if isinstance(self.available_addresses, dict) and self.available_addresses.get("error") != None: 
                    
            messagebox.showerror(title="Error", message= str(self.available_addresses.get("error")))

    def delete_selected(self): 

        selected_items = self.tree.selection()

        if not selected_items:

            messagebox.showerror(title="Error", message="Please select an item to delete.")
        
        else:
            response = messagebox.askquestion("Confirm", "Are you sure you want to proceed?")

            if response == 'yes':
                for selected in selected_items:
                
                    radio_mac_address = self.tree.item(selected)["values"][2]
                    result = deleteXbeeDetails(radio_mac_address)

                    if result.get("error") == None:

                        self.tree.delete(selected)
                 
                    else: 
                        
                        messagebox.showerror(title="Error", message= str(result.get("error")))

                self.refresh()
                messagebox.showinfo(title="Success", message="Entry deleted successfully.")
                

    def update_selected(self):

        self.selected_item = self.tree.selection()

        if not self.selected_item:

            messagebox.showerror(title="Error", message="Please select an item to update.")

        else:
            
            self.update_button.config(state="disabled")

            self.update_window = tk.Toplevel(self)
            self.update_window.title("Update Entry")

            self.update_entry_frame = tk.Frame(self.update_window, padx=20, pady=20)
            self.update_entry_frame.pack(fill="both")

            self.node_label = tk.Label(self.update_entry_frame, text="Node Identifier: ", width=20)
            self.node_label.grid(row=1, column=0, pady=10, sticky='w')
            self.node_input = tk.Entry(self.update_entry_frame, width=50)
            self.node_input.grid(row=1, column=1, pady=10, sticky='w')


            self.radio_label = tk.Label(self.update_entry_frame, text="Radio MAC Address: ", width=20)
            self.radio_label.grid(row=2, column=0, pady=10, sticky='w')
            self.radio_input = tk.Entry(self.update_entry_frame, width=50)
            self.radio_input.grid(row=2, column=1, pady=10, sticky='w')
            

            self.modbus_label = tk.Label(self.update_entry_frame, text="Modbus Start Address: ", width=20)
            self.modbus_label.grid(row=3, column=0, pady=10, sticky='w')
            self.modbus_input = tk.Entry(self.update_entry_frame, width=50)
            self.modbus_input.grid(row=3, column=1, pady=10, sticky='w')

            self.modbus_end_label = tk.Label(self.update_entry_frame, text="Modbus End Address: ", width=20)
            self.modbus_end_label.grid(row=4, column=0, pady=10, sticky='w')
            self.modbus_end_input = tk.Entry(self.update_entry_frame, width=50)
            self.modbus_end_input.grid(row=4, column=1, pady=10, sticky='w')
            

            self.update_entry = tk.Button(self.update_entry_frame, text="Update Entry", padx=20, pady=10,bg="blue", fg="white", command=self.click_update)
            self.update_entry.grid(row=5, column=0, columnspan=2, pady=10)

            self.old_node_identifier = self.tree.item(self.selected_item)["values"][1]
            self.old_mac_address = self.tree.item(self.selected_item)["values"][2]
            self.old_modbus_start_address = int(self.tree.item(self.selected_item)["values"][3])
            self.old_modbus_end_address = int(self.tree.item(self.selected_item)["values"][4])

            self.node_input.insert(0, self.old_node_identifier)
            self.radio_input.insert(0, self.old_mac_address)
            self.modbus_input.insert(0, self.old_modbus_start_address)
            self.modbus_end_input.insert(0, self.old_modbus_end_address)

            self.update_window.protocol("WM_DELETE_WINDOW", self.close_window)

            self.wait_window(self.update_window) # Wait for the update window to close before continuing

            self.update_button.config(state="normal")   

    def close_window(self):
        self.update_window.destroy()


    def click_update(self):

        self.json_data = {}
        self.result = []

        self.new_node_identifier = self.node_input.get()
        self.new_mac_address = self.radio_input.get()
        self.new_modbus_start_address = int(self.modbus_input.get())
        self.new_modbus_end_address = int(self.modbus_end_input.get())
    

        if self.new_node_identifier != self.old_node_identifier:

            self.json_data["xbeeNodeIdentifier"] = self.new_node_identifier 
            self.result.append(f"New Node Identifier: {self.new_node_identifier}")

        if self.new_mac_address != self.old_mac_address:

            self.json_data["xbeeMac"] = self.new_mac_address
            self.result.append(f"New Radio MAC Address: {self.new_mac_address}")


        if self.new_modbus_start_address != self.old_modbus_start_address:

            self.json_data["modbusStartAddress"] = int(self.new_modbus_start_address)
            self.result.append(f"New Modbus Start Address: {self.new_modbus_start_address}")
        
        if self.new_modbus_end_address != self.old_modbus_end_address:

            self.json_data["modbusEndAddress"] = int(self.new_modbus_end_address)
            self.result.append(f"New Modbus End Address: {self.new_modbus_end_address}")

            
        if self.json_data:
            joined_response = ', \n'.join(str(item) for item in self.result)
            response = messagebox.askyesno(title="Are you sure?", message=f"Are you fine with this update? \n\n{joined_response}")

            if response:

                result = updateXbeeDetails(self.old_mac_address, self.json_data)
                self.refresh() 

                if result.get("error") == None:

                    messagebox.showinfo(title="Success", message="Entry updated successfully.")
                    self.close_window()
                    self.update_button.config(state="normal")


                else:
                    messagebox.showerror(title="Error", message= str(result.get("error")))
                    # self.close_window()
                    # self.update_button.config(state="normal")
            

        else:
            messagebox.showerror(title="Error", message="No new update detected.")
            self.close_window()
            self.update_button.config(state="normal")

    def configure_button(self):
        filename = "modules/variables.py"

        with open(filename, "r") as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if line.startswith("prefferedRadioSerialNumber"):
                self.serial_number = line.split("=", 1)[1].strip()
                self.serial_number = self.serial_number.replace('"', '')

            if line.startswith("modbusPort"):
                self.modbus_port = line.split("=", 1)[1].strip()

            if line.startswith("incrementalModbusAddress"):
                self.incremental_address = line.split("=")[1].strip()
            

        self.configure_window = tk.Toplevel(self)
        self.configure_window.title("Configuration Window")

        self.configure_frame = tk.Frame(self.configure_window, padx=20, pady=20)
        self.configure_frame.pack(fill="both")

        self.serial_label = tk.Label(self.configure_frame, text="Serial Number: ", width=30)
        self.serial_label.grid(row=1, column=0, pady=10, sticky='w')
        self.serial_input = tk.Entry(self.configure_frame, width=50)
        self.serial_input.grid(row=1, column=1, pady=10, sticky='w')
        self.serial_input.insert(0, self.serial_number)

        self.modbus_label = tk.Label(self.configure_frame, text="Modbus Port: ", width=30)
        self.modbus_label.grid(row=2, column=0, pady=10, sticky='w')
        self.modbus_input = tk.Entry(self.configure_frame, width=50)
        self.modbus_input.grid(row=2, column=1, pady=10, sticky='w')
        self.modbus_input.insert(0, self.modbus_port)

        self.incremental_address_label = tk.Label(self.configure_frame, text="Incremental Modbus Address: ", width=30)
        self.incremental_address_label .grid(row=3, column=0, pady=10, sticky='w')
        self.incremental_address_input= tk.Entry(self.configure_frame, width=50)
        self.incremental_address_input.grid(row=3, column=1, pady=10, sticky='w')
        self.incremental_address_input.insert(0, self.incremental_address)

        self.save_button = tk.Button(self.configure_frame, text="Save", padx=20, pady=10,bg="blue", fg="white", command = self.read_serial_and_modbusport)
        self.save_button.grid(row=4, column=0, columnspan=2, pady=10)


        
    def read_serial_and_modbusport(self):
        filename = "modules/variables.py"
        update = False
        flag = False
        result = []

        with open(filename, "r") as file:
            lines = file.readlines()
    

        new_serial_number = str(self.serial_input.get())
        new_modbus_port = int(self.modbus_input.get()) 
        new_incremental_address = int(self.incremental_address_input.get()) 

        
        for i, line in enumerate(lines):
                if line.startswith("prefferedRadioSerialNumber"):
                    self.old_serial_number = line.split("=", 1)[1].strip()
                    self.old_serial_number = str(self.old_serial_number).replace('"', '')
                    if new_serial_number != self.old_serial_number:
                        new_line =  f'prefferedRadioSerialNumber = "{new_serial_number}"\n'
                        lines[i] = new_line
                        result.append(new_line)
                        update = True


                if line.startswith("modbusPort"):
                    self.old_modbus_port = int(line.split("=")[1].strip())
                    if new_modbus_port != self.old_modbus_port:
                        new_line = f'modbusPort = {new_modbus_port}\n'
                        lines[i] = new_line
                        result.append(new_line)
                        update = True

                if line.startswith("incrementalModbusAddress"):
                    self.old_incremental_address = int(line.split("=")[1].strip())
                    if new_incremental_address != self.old_incremental_address:
                        new_line =  f'incrementalModbusAddress = {new_incremental_address}\n'
                        lines[i] = new_line
                        result.append(new_line) 
                        update = True
                        flag = True


        
        if update:
            joined_response = ', \n'.join(str(item) for item in result)
            response = messagebox.askyesno(title="Are you sure?", message=f"Are you fine with this update? \n\n{joined_response}")

            if response:
                with open(filename, "w") as file:
                    file.writelines(lines)  

                if flag:
                    answer = messagebox.askyesno(title="Would you like to", message=f"Would you like to update the Modbus End Address? \n\nThis will update all the end addresses of the configured radios.")

                    if answer:
                        value = updateAllEndAddress(new_incremental_address)
                        print(value)
                        if value.get("error") == None:
                            messagebox.showinfo(title="Success", message= f'Successfully {value.get("success")} configured radios.')
                            self.refresh()
                        else:
                            messagebox.showerror(title="Error", message= str(value.get("error")))                       

                messagebox.showinfo(title="Success", message="Variable updated successfully.")



        
        else:
            messagebox.showerror(title="Error", message="No new update detected.")
 
            
        
        self.configure_window.destroy()

    def connection_status(self):
        status = radioConnectionStatus()

        if status == True:
            messagebox.showinfo(title="Connection Status", message="Radio is connected.")

        elif status == False or status == None:
            messagebox.showerror(title="Connection Status", message="Radio is not connected.")
        
        else:
            messagebox.showerror(title="Connection Status", message= f"Error: {status}")

    def select_usb(self):
        portValues = getListOfConnectedSerialDevice()

        message = """"""
        for value in portValues:
            message += f"Port: {value['port']} \nHWID: {value['hwid']}\n\n"

        messagebox.showinfo(title="Connected Serial Devices", message= f"""Connected Serial Devices:
                             \n{message}""")
        
my_app = Modbus_GUI()
my_app.mainloop()