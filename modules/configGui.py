import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from .dbIntegration import configureXbeeModbusStartAddress, retrieveAllConfiguredMacAddress, deleteXbeeDetails

class Modbus_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gateway GUI")
        self.geometry("800x650")

        self.title = tk.Label(self, text="CORS GATEWAY CONFIGURATION", font=("Arial", 20, "bold"))
        self.title.pack(pady=20)


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

        self.button = tk.Button(self, text = "Delete Selected", padx=20, pady=10,bg="blue", fg="white")
        self.button.pack(pady=10)
    
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
            else:
                error_message = result.get("error")
                messagebox.showerror(title="Error", message=error_message)

        except ValueError:
            messagebox.showerror(title="Invalid Input", message= "Please enter a valid Modbus Start Address (integer).")   

    def get_database(self):
        result = retrieveAllConfiguredMacAddress()

        for index, item in enumerate(result, start=1):
            self.tree.insert("", "end", values=(index, item[0], item[1], item[2]))

            
my_app = Modbus_GUI()
my_app.mainloop()