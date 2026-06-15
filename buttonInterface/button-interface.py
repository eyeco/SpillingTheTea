import tkinter as tk
from pythonosc.udp_client import SimpleUDPClient


numUsers = 3

class ButtonInterfaceApp(tk.Tk):
    def __init__(self, oscIP, oscPort):
        super().__init__()

        self.title("OSC Button Control")

        self.oscClient = SimpleUDPClient(oscIP, oscPort)

        self.oscIP = oscIP
        self.oscPort = oscPort

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 1. UI Setup
        self.oscStatusLabel = tk.Label(
            main, 
            text=f"OSC target: {oscIP}:{oscPort}", 
            font=("Arial", 12)
            )
        self.oscStatusLabel.pack()

        # btns = tk.Frame(main)
        # btns.pack(fill="x", expand=True)

        self.labels = [None] * numUsers

        for j in range(numUsers):
            btns = tk.LabelFrame(
                main,
                text=f"user#{j}",
                padx=10,
                pady=15)
            btns.pack(fill="x", expand=True, pady=5)

            for i in range(4):
                btns.grid_columnconfigure(i, weight=1, uniform="group1")
            
            tk.Button(
                btns, 
                text="Pinch", 
                bg="#4caf50",
                fg="#ffffff",
                activebackground="#43A047",
                font=("Arial", 18),
                command=lambda id=j: self.send("pinch",id),
                ).grid(row=0, column=0, padx=5, pady=(0,5), sticky="ew")#.pack(side="left", padx=(0, 8))
            tk.Button(
                btns, 
                text="Tripod", 
                bg="#2196f3",
                fg="#ffffff",
                activebackground="#1e88e5",
                font=("Arial", 18),
                command=lambda id=j: self.send("tripod",id),
                ).grid(row=0, column=1, padx=5, pady=(0,5), sticky="ew")#.pack(side="left", padx=(0, 8))
            tk.Button(
                btns, 
                text="Power", 
                bg="#9c27b0",
                fg="#ffffff",
                activebackground="#43a047",
                font=("Arial", 18),
                command=lambda id=j: self.send("power",id),
                ).grid(row=0, column=2, padx=(5,25), pady=(0,5), sticky="ew")#).pack(side="left", padx=(0, 28))

            tk.Button(
                btns, 
                text="Relax", 
                bg="#f57c00",
                fg="#ffffff",
                activebackground="#ef6c00",
                font=("Arial", 18),
                command=lambda id=j: self.send("relax",id),
                ).grid(row=0, column=3, padx=5, pady=(0,5), sticky="ew")#).pack(side="left", padx=(0, 8))

            #self.statusLabel = tk.Label(
            #self.statusLabel.pack(pady=(10, 20))
            self.labels[j] = tk.Label(
                btns, 
                text="Status: IDLE", 
                font=("Arial", 12)
                )
            self.labels[j].grid(row=1, column=0, columnspan=4, padx=5, sticky="ew")#.pack(pady=(10, 20))

        self.update_idletasks() #calc content size _before_ locking resizing
        self.resizable(False, False)


    def send(self, command, id):
        print(f"[sending] command: '{command}' for user {id}")

        value = 1

        try:
            msg = f"/{command}/{id}"
            # send_message(OSC_Address, Value)
            self.oscClient.send_message(msg, value)
            
            # Update GUI status
            #self.statusLabel.config(text=f"Sent: {msg} -> {value}")
            self.labels[id].config(text=f"Sent: {msg} -> {value}")
            print(f"OSC Sent to {self.oscIP}:{self.oscPort}: {command} -> {value}")
            
        except Exception as e:
            self.status_label.config(text=f"Error sending message!")
            print(f"Failed to send OSC: {e}")

# --- EXECUTION ROOT ---
if __name__ == "__main__":
    app = ButtonInterfaceApp("127.0.0.1", 6667) 
    
    # Python hands full execution control over to the UI layout here
    app.mainloop()