import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from .dbIntegration import configureXbeeModbusStartAddress, retrieveAllConfiguredMacAddress, deleteXbeeDetails, updateXbeeDetails

class Modbus_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gateway GUI")
        self.geometry("800x650")

        self.head = tk.Label(self, text="CORS GATEWAY CONFIGURATION", font=("Arial", 20, "bold"))
        self.head.pack(pady=20)


        self.label = tk.Label(self, text="Add New Entry")
        self.label.pack(pady=10)

        self.add_entry_frame = tk.Frame(self)
        self.add_entry_frame.pack(fill="both")

        self.radio_address_label = tk.Label(self.add_entry_frame, text="Radio MAC Address: ", width=40)
        self.radio_address_label.grid(row=1, column=0,padx=10, pady=10, sticky='w')
        self.radio_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.radio_address_input.grid(row=1, column=1, pady=10, sticky='w')
        

        self.modbus_address_label = tk.Label(self.add_entry_frame, text="Modbus Start Address: ", width=40)
        self.modbus_address_label.grid(row=2, column=0, padx=10, pady=10, sticky='w')
        self.modbus_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.modbus_address_input.grid(row=2, column=1, pady=10, sticky='w')


        self.node_identifier_label = tk.Label(self.add_entry_frame, text="Node Identifier: ", width=40)
        self.node_identifier_label.grid(row=3, column=0, padx=10, pady=10, sticky='w')
        self.node_identifier_input = tk.Entry(self.add_entry_frame, width=50)
        self.node_identifier_input.grid(row=3, column=1, pady=10, sticky='w')



        self.button = tk.Button(self, text="Add to Database", padx=20, pady=10,bg="blue", fg="white", command=self.on_click)
        self.button.pack(pady=10)

        #Let's talk database here
        #database entries
        self.show_entry_frame = ttk.LabelFrame(self, border=1, text="Database Entries", padding=10)
        self.show_entry_frame.pack(fill="both")

        # Treeview with scrollbar
        self.tree = ttk.Treeview(self.show_entry_frame)

        # Define columns
        self.tree['columns'] = ('S/N', 'RadioMACAddress', 'ModbusAddress', "Node Identifier")

        # Format columns
        self.tree.column("#0", width=0, stretch=tk.NO)  # Hide first empty column
        
        self.tree.column("S/N", anchor=tk.CENTER, width=50)
        self.tree.column("RadioMACAddress", anchor=tk.CENTER, width=250)
        self.tree.column("ModbusAddress", anchor=tk.CENTER, width=200)
        self.tree.column("Node Identifier", anchor=tk.CENTER, width=250)

        self.tree.heading("S/N", text="S/N")
        self.tree.heading("RadioMACAddress", text="Radio MAC Address")
        self.tree.heading("ModbusAddress", text="Modbus Start Address")
        self.tree.heading("Node Identifier", text="Node Identifier")

        self.tree.pack()

        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=10)

        self.button = tk.Button(self.button_frame, text = "Delete Selected", padx=20, pady=10,bg="blue", fg="white", command=self.delete_selected)
        self.button.pack(side=tk.LEFT)

        self.update_button = tk.Button(self.button_frame, text = "Update Selected", padx=20, pady=10,bg="blue", fg="white", command=self.update_selected)
        self.update_button.pack(padx=30)
    
        self.get_database()



    def on_click(self):
        self.radio_address = self.radio_address_input.get()
        self.modbus_address = self.modbus_address_input.get()
        self.node_identifier = self.node_identifier_input.get()

        try:
            result = configureXbeeModbusStartAddress(self.radio_address, int(self.modbus_address), self.node_identifier)

            if result.get("error") == None:
                self.radio_address_input.delete(0, tk.END)
                self.modbus_address_input.delete(0, tk.END) 
                self.node_identifier_input.delete(0, tk.END)

                messagebox.showinfo(title="Success", message="Entry added successfully.")
                self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
                self.get_database()  # Repopulate the treeview with updated data
            else:
                error_message = result.get("error")
                messagebox.showerror(title="Error", message=error_message)

        except ValueError:
            messagebox.showerror(title="Invalid Input", message= "Please enter a valid Modbus Start Address (integer).")   

    def get_database(self):
        result = retrieveAllConfiguredMacAddress()

        for index, item in enumerate(result, start=1):
            self.tree.insert("", "end", values=(index, item[0], item[1], item[2]))

    def delete_selected(self): 
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror(title="Error", message="Please select an item to delete.")
        
        else:
            response = messagebox.askquestion("Confirm", "Are you sure you want to proceed?")

            if response == 'yes':
                radio_mac_address = self.tree.item(selected_item)["values"][1]
                result = deleteXbeeDetails(radio_mac_address)
                if result.get("success") != None:
                    messagebox.showinfo(title="Success", message="Entry deleted successfully.")
                    self.tree.delete(selected_item)
                    self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
                    self.get_database()  # Repopulate the treeview with updated data

    def update_selected(self):
        self.selected_item = self.tree.selection()
        if not self.selected_item:
            messagebox.showerror(title="Error", message="Please select an item to update.")

        else:
            self.update_window = tk.Toplevel(self)
            self.update_window.title("Update Entry")

            self.update_entry_frame = tk.Frame(self.update_window, padx=20, pady=20)
            self.update_entry_frame.pack(fill="both")

            self.radio_label = tk.Label(self.update_entry_frame, text="Radio MAC Address: ", width=20)
            self.radio_label.grid(row=1, column=0, pady=10, sticky='w')
            self.radio_input = tk.Entry(self.update_entry_frame, width=50)
            self.radio_input.grid(row=1, column=1, pady=10, sticky='w')
            

            self.modbus_label = tk.Label(self.update_entry_frame, text="Modbus Start Address: ", width=20)
            self.modbus_label.grid(row=2, column=0, pady=10, sticky='w')
            self.modbus_input = tk.Entry(self.update_entry_frame, width=50)
            self.modbus_input.grid(row=2, column=1, pady=10, sticky='w')


            self.node_label = tk.Label(self.update_entry_frame, text="Node Identifier: ", width=20)
            self.node_label.grid(row=3, column=0, pady=10, sticky='w')
            self.node_input = tk.Entry(self.update_entry_frame, width=50)
            self.node_input.grid(row=3, column=1, pady=10, sticky='w')

            self.update_entry = tk.Button(self.update_entry_frame, text="Update Entry", padx=20, pady=10,bg="blue", fg="white", command=self.click_update)
            self.update_entry.grid(row=4, column=0, columnspan=2, pady=10)

            self.old_mac_address = self.tree.item(self.selected_item)["values"][1]
            self.old_modbus_address = int(self.tree.item(self.selected_item)["values"][2])
            self.old_node_identifier = self.tree.item(self.selected_item)["values"][3]

            self.radio_input.insert(0, self.old_mac_address)
            self.modbus_input.insert(0, self.old_modbus_address)
            self.node_input.insert(0, self.old_node_identifier)


    def click_update(self):
        self.json_data = {}

        self.new_mac_address = self.radio_input.get()
        self.new_modbus_address = int(self.modbus_input.get())
        self.new_node_identifier = self.node_input.get()
    
            
        if self.new_mac_address != self.old_mac_address:
            self.json_data["xbeeMac"] = self.new_mac_address
        if self.new_modbus_address != self.old_modbus_address:
            self.json_data["modbusStartAddress"] = int(self.new_modbus_address)
        if self.new_node_identifier != self.old_node_identifier:
            self.json_data["xbeeNodeIdentifier"] = self.new_node_identifier

        if self.json_data:
            updateXbeeDetails(self.old_mac_address, self.json_data)
            self.tree.delete(*self.tree.get_children())  # Clear the treeview before repopulating
            self.get_database() 
            messagebox.showinfo(title="Success", message="Entry updated successfully.")


        else:
            messagebox.showerror(title="Error", message="No new update detected.")

        

        

        self.update_window.destroy()
        
            
my_app = Modbus_GUI()
my_app.mainloop()