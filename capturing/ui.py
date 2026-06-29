# ui.py

import tkinter as tk
import threading

class UnifiedLabApp:
    def __init__(self, window):
        self.window = window
        self.window.title("OSC & Video Control")
        self.window.geometry("400x200")
        self.window.resizable(False, False)
        
        # 1. UI Setup
        self.status_label = tk.Label(
            window, 
            text="Status: IDLE", 
            font=("Arial", 12)
            )
        self.status_label.pack(pady=20)
        
        self.btn = tk.Button(
            window, 
            text="Start", 
            font=("Arial", 18),
            command=self.uiOnStartStop,
            padx=10,
            pady=10
            )
        self.btn.pack(pady=10)
        
        # # 2. Setup the OSC Server Architecture
        # self.osc_dispatcher = dispatcher.Dispatcher()
        # # Map your network endpoints to internal methods
        # self.osc_dispatcher.map("/stop", self.osc_trigger_stop)
        
        # self.osc_server = osc_server.ThreadingOSCUDPServer(
        #     ("127.0.0.1", self.osc_port), self.osc_dispatcher
        # )
        
        # # 3. CRITICAL: Launch the OSC server on its own background thread right away
        # self.network_thread = threading.Thread(
        #     target=self.osc_server.serve_forever, 
        #     daemon=True # Ensures the server dies when you close the UI window
        # )
        # self.network_thread.start()
        # print(f"[Network] OSC Server listening live on port {self.osc_port}...")

    # # --- INCOMING BACKGROUND OSC COMMANDS ---
    # def osc_trigger_stop(self, address, *args):
    #     print(f"[OSC Receipt] Remote stop command received via network path: {address}")
        
    #     # Thread safety rule: Always hand UI transitions back to the main thread!
    #     self.window.after(0, self.execute_stop_sequence)

    # --- LOCAL CLICK TRIGGERS ---
    def uiOnStartStop(self):
        print("[UI Click] Manual start/stop initiated.")
        self.status_label.config(text="Status: CAPTURING...", fg="green")
        self.btn.config(
            text="Stop",
            bg="orange"
        )
        
    #     # Dynamically launch Thread 3 for the camera capturing routine
    #     threading.Thread(target=self.video_worker_loop, daemon=True).start()


    # def execute_stop_sequence(self):
    #     """Unified stop routine that can be safely triggered by UI or OSC Network."""
    #     if not self.is_capturing:
    #         return
            
    #     print("[System] Executing blocking teardown routine...")
    #     self.status_label.config(text="Status: STOPPING...", fg="orange")
    #     self.is_capturing = False
    #     # (Insert your process.communicate() and log flushing code here)
        
    #     self.status_label.config(text="Status: IDLE", fg="gray")

# --- EXECUTION ROOT ---
if __name__ == "__main__":
    root = tk.Tk()
    app = UnifiedLabApp(root) 
    
    # Python hands full execution control over to the UI layout here
    root.mainloop()