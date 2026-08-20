import tkinter as tk
import re
import threading

from pythonosc import dispatcher, osc_server
from pythonosc.udp_client import SimpleUDPClient
from pathlib import Path

sessionOutDir = "L:\\stt"
#sessionOutDir = "C:\\Users\\Festival2026\\Desktop\\stt\\recordings"

oscPortIn = 6668

oscPortSqid = 6667
oscPortCapture = 6669
oscStartCommand = "/start"
oscStopCommand = "/stop"
oscMarkerCommand = "/marker"

pathPattern = re.compile(r"^session(\d+)$")

def getSessionNumber(path: str | Path) -> int:
    path = Path(path)
    nums = []

    if path.exists():
        for file in path.iterdir():
            if file.is_dir():
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

        self.protocol("WM_DELETE_WINDOW", self.onClosing)

        self.title("OSC Button Control")

        self.oscClientSqid = SimpleUDPClient("127.0.0.1", oscPortSqid)
        self.oscClientCapture = SimpleUDPClient("127.0.0.1", oscPortCapture)

        main = tk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 1. UI Setup
        self.oscStatusLabel = tk.Label(
            main, 
            text=f"OSC target: {oscPortSqid}, {oscPortCapture}", 
            font=("Arial", 12)
            )
        self.oscStatusLabel.pack()

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
                width = 5,
                text="<dummy>\n<dummy>\n<dummy>\n<dummy>\n<dummy>", 
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

        status_frame = tk.Frame(self.vid)
        status_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5
        )

        self.deviceStatus = {}

        devices = [
            ("vid0", "V1"),
            ("vid1", "V2"),
            ("vid2", "V3"),
            ("vid3", "V4"),
            ("aud0", "AUD"),
        ]

        for col, (devID, name) in enumerate(devices):
            status_frame.grid_columnconfigure(col, weight=1)

            box = tk.Frame(status_frame)
            box.grid(row=0, column=col, padx=2)

            # Indicator light (Default: Red / Offline)
            led = tk.Label(box, text="●", fg="#f44336", font=("Arial", 16))
            led.pack(side="left")

            lbl = tk.Label(box, text=name, font=("Arial", 10, "bold"))
            lbl.pack(side="left", padx=(2, 0))

            self.deviceStatus[devID] = led

        self.update_idletasks() #calc content size _before_ locking resizing
        self.resizable(False, False)

        self.recording = False

        self.pressureDebugValues = [[0] * 5] * numUsers
        for i in range(numUsers):
            self.updatePressureDebugLabels(i)
        self.updateSessionLabel()
        self.updateRecordButton()

        self.startOSCListener()

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

    def updatePressureDebugLabels(self,userID):

        if userID < 0 or userID >= numUsers:
            print(f"ERROR: invalid user ID: {userID}")
            return

        self.pressureDebug[userID].config(
            text = '\n'.join(f"{x:.3f}" for x in self.pressureDebugValues[userID])
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
            self.oscStatusLabel.config(
                text=f"Error sending message!"
                )
            print(f"Failed to send OSC: {e}")

    def startOSCListener(self):
        disp = dispatcher.Dispatcher()
        disp.set_default_handler(self.handleOSC)

        self.server = osc_server.ThreadingOSCUDPServer(
            ("127.0.0.1", oscPortIn), disp
        )

        self.server.block_on_close = False
        self.server.daemon_threads = True

        self.is_running = True
        # daemon=True ensures the thread terminates automatically when the GUI closes
        serverThread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        serverThread.start()

    def handleOSC(self, address, *args):
        if not getattr(self, "is_running", True):
            return
        
        # Schedule the UI update onto Tkinter's main execution loop
        try:
            self.after(0, self.updateLabelSafe, address, args)
        except (tk.TclError, RuntimeError):
            pass

    def onClosing(self):
        self.is_running = False

        if hasattr(self, "server"):

            # def stopServer():
            #     try:
                    print("shutdown")
                    self.server.shutdown()
                    print("server_close")
                    self.server.server_close()
                # except Exception:
                #     pass

        #threading.Thread(target=stopServer, daemon=True).start()

        print("destroy")
        self.destroy()  # Close the window without waiting
        print("done")

    def updateLabelSafe(self, address, args):
        # Executes safely on the main GUI thread.
        #self.status_label["text"] = f"Received {address}: {args}"

        #print(f"{address} -> {str(args)}")

        subs = address.strip("/").split("/")
        if len(subs) < 1:
            print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
            return

        args = (
            list(args)
            if isinstance(args, (list, tuple))
            else ([] if args is None else [args])
        )

        if subs[0] == "alive":
            if len(subs) != 2:
                print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
                return

            if subs[1] == "audio":
                if len(args) < 0:
                    print(f"ERROR: no arguments for '{address}'")
                    return
                elif len(args) > 1:
                    print(f"WARNING: too many arguments for '{address}': {len(args)}")

                for i in range(len(args)):
                    self.setDeviceStatus(f"aud{i}", bool(args[0]))

            elif subs[1] == "video":
                if len(args) < 0:
                    print(f"ERROR: no arguments for '{address}'")
                    return
                elif len(args) > 4:
                    print(f"WARNING: too many arguments for '{address}': {len(args)}")

                for i in range(len(args)):
                    self.setDeviceStatus(f"vid{i}", bool(args[i]))

            else:
                print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
                return
        elif subs[0] == "glove":
            if len(subs) != 3:
                print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
                return
            
            if subs[1] == "diff":

                userID = int(subs[2])
                if userID < 0 or userID > 2:
                    print(f"ERROR: invalid user ID: {userID}")
                    return

                if len(args) == 0:
                    print(f"ERROR: no arguments for '{address}'")
                    return
                if len(args) > 5:
                    print(f"WARNING: too few arguments for '{address}': {len(args)}")

                for i in range(len(args)):
                    self.pressureDebugValues[userID][i] = float(args[i])

            else:
                print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
                return

            self.updatePressureDebugLabels(userID)

        else:
            print(f"ERROR: unexpected OSC message (or wrong format): '{address}'")
            return


    def setDeviceStatus(self, devID: str, online: bool):
        color = "#4caf50" if online else "#f44336"  # Green if online, Red if offline
        self.deviceStatus[devID].config(fg=color)


# --- EXECUTION ROOT ---
if __name__ == "__main__":
    app = ButtonInterfaceApp() 
    
    # Python hands full execution control over to the UI layout here
    app.mainloop()