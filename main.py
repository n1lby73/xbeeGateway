import tkinter as tk
from tkinter import ttk

class Modbus_GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Modbus GUI")
        self.geometry("800x600")

        self.title = tk.Label(self, text="CORS MODBUS SERVER", font=("Arial", 20, "bold"))
        self.title.pack(pady=20)


        self.label = tk.Label(self, text="Add New Entry")
        self.label.pack(pady=10)

        self.add_entry_frame = tk.Frame(self)
        self.add_entry_frame.pack(fill="both")

        self.radio_address_label = tk.Label(self.add_entry_frame, text="Radio Address: ", width=40)
        self.radio_address_label.grid(row=1, column=0,padx=10, pady=10, sticky='w')
        self.radio_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.radio_address_input.grid(row=1, column=1, pady=10, sticky='w')

        self.modbus_address_label = tk.Label(self.add_entry_frame, text="Modbus Start Address: ", width=40)
        self.modbus_address_label.grid(row=2, column=0, padx=10, pady=10, sticky='w')
        self.modbus_address_input = tk.Entry(self.add_entry_frame, width=50)
        self.modbus_address_input.grid(row=2, column=1, pady=10, sticky='w')

        self.button = tk.Button(self, text="Add to Database", padx=20, pady=10,bg="blue", fg="white")
        self.button.pack(pady=10)


        #database entries
        self.show_entry_frame = ttk.LabelFrame(self, border=1, text="Database Entries", padding=10)
        self.show_entry_frame.pack(fill="both")

        # Treeview with scrollbar
        self.tree = ttk.Treeview(self.show_entry_frame, columns=('ID', 'RadioAddress', 'ModbusAddress'), show='headings')

        # Define columns
        self.tree.heading('ID', text='ID')
        self.tree.heading('RadioAddress', text='Radio Address')
        self.tree.heading('ModbusAddress', text='Modbus Start Address')
        
        # # Set column widths
        # self.tree.column('ID', width=10, anchor=tk.CENTER)
        # self.tree.column('RadioAddress', width=150, anchor=tk.CENTER)
        # self.tree.column('ModbusAddress', width=150, anchor=tk.CENTER)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.show_entry_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        
        # Configure grid weights
        self.show_entry_frame.rowconfigure(0, weight=1)
        self.show_entry_frame.columnconfigure(0, weight=1)


        self.button = tk.Button(self, text = "Delete Selected", padx=20, pady=10,bg="blue", fg="white")
        self.button.pack(pady=10)



    def on_button_click(self):
        self.label.config(text="Button Clicked!")

my_app = Modbus_GUI()
my_app.mainloop()