import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
from .dbIntegration import configureXbeeRadio, retrieveAllConfiguredMacAddress, deleteXbeeDetails, updateXbeeDetails

class Modbus_GUI(tk.Tk):

    def __init__(self):

        super().__init__()
        self.title("Gateway GUI")
        self.geometry("800x650")

        self.head = tk.Label(self, text="CORS GATEWAY CONFIGURATION", font=("Arial", 20, "bold"))
        self.head.pack(pady=10)


        self.label = tk.Label(self, text="Add New Entry")
        self.label.pack(pady=10)

        self.add_entry_frame = tk.Frame(self)
        self.add_entry_frame.pack(fill="both")

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
    

        self.button = tk.Button(self, text="Add to Database", padx=20, pady=10,bg="blue", fg="white", command=self.on_click)
        self.button.pack(pady=10)

        # refresh_image_path = "refresh.png"  
        # refresh_image = Image.open(refresh_image_path)
        # refresh_image = refresh_image.resize((30, 30), Image.LANCZOS)
        # refresh_image = ImageTk.PhotoImage(refresh_image)
        # self.refresh_image = refresh_image

        # refresh_button = tk.Button(self, image=self.refresh_image)
        # refresh_button.pack( padx=10, pady=10)


        #Let's talk database here
        self.show_entry_frame = ttk.LabelFrame(self, border=1, text="Configured Xbee Radios", padding=5)
        self.show_entry_frame.pack(fill="both")

        self.search_frame = tk.Frame(self.show_entry_frame)
        self.search_frame.pack()

        self.search_bar = tk.Entry(self.search_frame, width=50)
        self.search_bar.grid(row=0, column=0,  sticky='w')

        self.find_button = tk.Button(self.search_frame, text="Find", padx=20, bg="blue", fg="white")
        self.find_button.grid(row=0, column=1, padx=10, pady=10)

        self.tree = ttk.Treeview(self.show_entry_frame)

        # Define columns
        self.tree['columns'] = ('S/N',"Node Identifier", 'RadioMACAddress','ModbusAddress',  "ModbusEndAddress" )

        # Format columns
        self.tree.column("#0", width=0, stretch=tk.NO)  # Hide first empty column
        
        self.tree.column("S/N", anchor=tk.CENTER, width=30)
        self.tree.column("Node Identifier", anchor=tk.CENTER, width=150)
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

        self.update_button = tk.Button(self.button_frame, text = "Update Selected", padx=20, pady=10,bg="blue", fg="white", command=self.update_selected)
        self.update_button.pack(padx=30)

    
        self.get_database()

    def find(self):
        self.search = self.search_bar.get()

        
    def on_click(self):

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

    def get_database(self):

        result = retrieveAllConfiguredMacAddress()

        for index, item in enumerate(result, start=1):

            self.tree.insert("", "end", values=(index, item[0], item[1], item[2], item[3]))

        if isinstance(result, dict) and result.get("error") != None: 
                    
            messagebox.showerror(title="Error", message= str(result.get("error")))

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
            
                self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
                self.get_database()  # Repopulate the treeview with updated data
                messagebox.showinfo(title="Success", message="Entry deleted successfully.")
                

    def update_selected(self):

        self.selected_item = self.tree.selection()

        if not self.selected_item:

            messagebox.showerror(title="Error", message="Please select an item to update.")

        else:

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
            

            self.update_entry = tk.Button(self.update_entry_frame, text="Update Entry", padx=20, pady=10,bg="blue", fg="white", command=self.click_update)
            self.update_entry.grid(row=4, column=0, columnspan=2, pady=10)

            self.old_node_identifier = self.tree.item(self.selected_item)["values"][1]
            self.old_mac_address = self.tree.item(self.selected_item)["values"][2]
            self.old_modbus_address = int(self.tree.item(self.selected_item)["values"][3])

            self.node_input.insert(0, self.old_node_identifier)
            self.radio_input.insert(0, self.old_mac_address)
            self.modbus_input.insert(0, self.old_modbus_address)


    def click_update(self):

        self.json_data = {}
        self.result = []

        self.new_node_identifier = self.node_input.get()
        self.new_mac_address = self.radio_input.get()
        self.new_modbus_address = int(self.modbus_input.get())
    

        if self.new_node_identifier != self.old_node_identifier:

            self.json_data["xbeeNodeIdentifier"] = self.new_node_identifier 
            self.result.append(f"New Node Identifier: {self.new_node_identifier}")

        if self.new_mac_address != self.old_mac_address:

            self.json_data["xbeeMac"] = self.new_mac_address
            self.result.append(f"New Radio MAC Address: {self.new_mac_address}")


        if self.new_modbus_address != self.old_modbus_address:

            self.json_data["modbusStartAddress"] = int(self.new_modbus_address)
            self.result.append(f"New Modbus Start Address: {self.new_modbus_address}")

            
        if self.json_data:
            joined_response = ', \n'.join(str(item) for item in self.result)
            response = messagebox.askyesno(title="Are you sure?", message=f"Are you fine with this update? \n\n{joined_response}")

            if response:

                result = updateXbeeDetails(self.old_mac_address, self.json_data)
                self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
                self.get_database() 

                if result.get("error") == None:

                    messagebox.showinfo(title="Success", message="Entry updated successfully.")
                    self.update_window.destroy()


                else:
                    
                    messagebox.showerror(title="Error", message= str(result.get("error")))
            

        else:

            messagebox.showerror(title="Error", message="No new update detected.")

          
my_app = Modbus_GUI()
my_app.mainloop()