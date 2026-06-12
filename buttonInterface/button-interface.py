import tkinter as tk
from pythonosc.udp_client import SimpleUDPClient

class ButtonInterfaceApp(tk.Tk):
    def __init__(self, oscIP, oscPort):
        super().__init__()

        self.title("OSC Button Control")
        self.geometry("400x160")
        self.resizable(False, False)

        self.oscClient = SimpleUDPClient(oscIP, oscPort)

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 1. UI Setup
        self.oscStatusLabel = tk.Label(
            main, 
            text=f"OSC target: {oscIP}:{oscPort}", 
            font=("Arial", 12)
            )
        self.oscStatusLabel.pack(pady=(0, 15))

        btns = tk.Frame(main)
        btns.pack(fill="x", expand=True)

        for i in range(4):
            btns.grid_columnconfigure(i, weight=1, uniform="group1")
        
        tk.Button(
            btns, 
            text="Pinch", 
            bg="#4caf50",
            fg="#ffffff",
            activebackground="#43A047",
            font=("Arial", 18),
            command=lambda: self.send("pinch"),
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            btns, 
            text="Tripod", 
            bg="#2196f3",
            fg="#ffffff",
            activebackground="#1e88e5",
            font=("Arial", 18),
            command=lambda: self.send("tripod"),
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            btns, 
            text="Power", 
            bg="#9c27b0",
            fg="#ffffff",
            activebackground="#43a047",
            font=("Arial", 18),
            command=lambda: self.send("power"),
            ).pack(side="left", padx=(0, 28))

        tk.Button(
            btns, 
            text="Relax", 
            bg="#f57c00",
            fg="#ffffff",
            activebackground="#ef6c00",
            font=("Arial", 18),
            command=lambda: self.send("relax"),
            ).pack(side="left", padx=(0, 8))

        self.statusLabel = tk.Label(
            main, 
            text="Status: IDLE", 
            font=("Arial", 12)
            )
        self.statusLabel.pack(pady=(10, 20))

    def send(self, command):
        print(f"[sending] command: '{command}'")
        self.statusLabel.config(text=f"Status: {command}")

        value = 1

        try:
            # send_message(OSC_Address, Value)
            self.oscClient.send_message(command, value)
            
            # Update GUI status
            self.statusLabel.config(text=f"Sent: /{command} -> {value}")
            print(f"OSC Sent to {command}: {value}")
            
        except Exception as e:
            self.status_label.config(text=f"Error sending message!")
            print(f"Failed to send OSC: {e}")

# --- EXECUTION ROOT ---
if __name__ == "__main__":
    app = ButtonInterfaceApp("127.0.0.1", 6667) 
    
    # Python hands full execution control over to the UI layout here
    app.mainloop()