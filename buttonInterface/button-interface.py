import tkinter as tk
import re

from pythonosc.udp_client import SimpleUDPClient
from pathlib import Path

sessionOutDir = "L:\\stt"

oscPortSqid = 6667
oscPortCapture = 6669
oscStartCommand = "/start"
oscStopCommand = "/stop"
oscMarkerCommand = "/marker"

pathPattern = re.compile(r"^session(\d+)-log\.csv$")

def getSessionNumber(path: str | Path) -> int:
    path = Path(path)
    
    nums = []

    if path.exists():
        for file in path.iterdir():
            if file.is_file():
                match = pathPattern.match(file.name)
                if match:
                    nums.append(int(match.group(1)))
                
    return max(nums) + 1 if nums else 0

sessionID = getSessionNumber(sessionOutDir)
print(f"starting with session #{sessionID}")

numUsers = 3

class ButtonInterfaceApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("OSC Button Control")

        self.oscClientSqid = SimpleUDPClient("127.0.0.1", oscPortSqid)
        self.oscClientCapture = SimpleUDPClient("127.0.0.1", oscPortCapture)

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 1. UI Setup
        # self.oscStatusLabel = tk.Label(
        #     main, 
        #     text=f"OSC target: {oscIP}:{oscPort}", 
        #     font=("Arial", 12)
        #     )
        # self.oscStatusLabel.pack()

        # btns = tk.Frame(main)
        # btns.pack(fill="x", expand=True)

        self.statusLabels = [None] * numUsers
        self.pressureDebug = [None] * numUsers

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
                width=10,
                bg="#4caf50",
                fg="#ffffff",
                activebackground="#43A047",
                font=("Arial", 18),
                command=lambda id=j: self.send("pinch",id),
                ).grid(row=0, column=0, padx=5, pady=(0,5), sticky="ew")#.pack(side="left", padx=(0, 8))
            tk.Button(
                btns, 
                text="Tripod", 
                width=10,
                bg="#2196f3",
                fg="#ffffff",
                activebackground="#1e88e5",
                font=("Arial", 18),
                command=lambda id=j: self.send("tripod",id),
                ).grid(row=0, column=1, padx=5, pady=(0,5), sticky="ew")#.pack(side="left", padx=(0, 8))
            tk.Button(
                btns, 
                text="Power", 
                width=10,
                bg="#9c27b0",
                fg="#ffffff",
                activebackground="#43a047",
                font=("Arial", 18),
                command=lambda id=j: self.send("power",id),
                ).grid(row=0, column=2, padx=(5,25), pady=(0,5), sticky="ew")#).pack(side="left", padx=(0, 28))

            tk.Button(
                btns, 
                text="Relax", 
                width=10,
                bg="#f57c00",
                fg="#ffffff",
                activebackground="#ef6c00",
                font=("Arial", 18),
                command=lambda id=j: self.send("relax",id),
                ).grid(row=0, column=3, padx=5, pady=(0,5), sticky="ew")#).pack(side="left", padx=(0, 8))

            self.statusLabels[j] = tk.Label(
                btns, 
                text="Status: IDLE", 
                font=("Arial", 12)
                )
            self.statusLabels[j].grid(row=1, column=0, columnspan=4, padx=5, sticky="ew")#.pack(pady=(10, 20))

            self.pressureDebug[j] = tk.Label(
                btns, 
                text="Debug\nDebug\nDebug\nDebug\nDebug", 
                font=("Arial", 10)
                )
            self.pressureDebug[j].grid(row=0, column=4, rowspan=2, padx=25, sticky="ew")#.pack(pady=(10, 20))

        self.vid = tk.LabelFrame(
            main, 
            text="capture", 
            font=("Arial", 12)
            )
        self.vid.pack()

        self.sessionLabel = tk.Label(
                self.vid, 
                text="<dummy>", 
                font=("Arial", 12)
                )
        self.sessionLabel.grid(row=0, column=0, padx=5, pady=(0,5), sticky="ew")#.pack(pady=(10, 20))

        self.recordButton = tk.Button(
            self.vid,
            text="<dummy>", 
            width=10,
            bg="#14a800",
            fg="#ffffff",
            activebackground="#ef6c00",
            font=("Arial", 18),
            command=self.uiRecordButton,
            )
        self.recordButton.grid(row=0, column=1, padx=5, pady=(0,5), sticky="ew")#).pack(side="left", padx=(0, 8))

        self.update_idletasks() #calc content size _before_ locking resizing
        self.resizable(False, False)

        self.recording = False

        self.updateSessionLabel()
        self.updateRecordButton()

    def updateSessionLabel(self):
        self.sessionLabel.config(
            text = f"session: {sessionID}"
        )

    def updateRecordButton(self):
        if self.recording:
            self.recordButton.config(
                text="Stop",
                bg="#fcac00",
                fg="#000000"
            )
        else:
            self.recordButton.config(
                text="Start",
                bg="#14a800",
                fg="#ffffff"
            )

    def uiRecordButton(self):
        global sessionID

        print("[UI Click] Manual start/stop initiated.")

        self.recording = not self.recording

        if self.recording:
            print(f"startig recordinng of session #{sessionID}")

            msg = oscStartCommand
            name = f"session{sessionID:03d}"
            self.oscClientCapture.send_message(msg, name)
            print(f"OSC Sent to {oscPortCapture}: {msg} -> {name}")
        else:
            print(f"stopping recordinng of session #{sessionID}")
            sessionID = sessionID + 1
            self.updateSessionLabel()

            msg = oscStopCommand
            self.oscClientCapture.send_message(msg,None)
            print(f"OSC Sent {oscPortCapture}: {msg}")

        self.updateRecordButton()

    def send(self, command, id):
        print(f"[sending] command: '{command}' for user {id}")

        value = 1

        try:
            msg = f"/{command}/{id}"
            # send_message(OSC_Address, Value)
            self.oscClientSqid.send_message(msg, value)
            
            # Update GUI status
            #self.statusLabel.config(text=f"Sent: {msg} -> {value}")
            self.statusLabels[id].config(text=f"Sent: {command} -> {value}")
            print(f"OSC Sent to {oscPortSqid}: {msg} -> {value}")

            msg = "/investigator" + msg
            self.oscClientCapture.send_message(msg, 1)
            print(f"OSC Sent to {oscPortCapture}: {msg} -> {value}")
            
        except Exception as e:
            self.status_label.config(text=f"Error sending message!")
            print(f"Failed to send OSC: {e}")

# --- EXECUTION ROOT ---
if __name__ == "__main__":
    app = ButtonInterfaceApp() 
    
    # Python hands full execution control over to the UI layout here
    app.mainloop()