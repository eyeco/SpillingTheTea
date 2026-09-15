# utils.py

import os
import csv
import time

import threading
from datetime import datetime

# ANSI escape codes for color formatting on console
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

outdir = "C:\\stt\\recordings"

def error(str):
    print(f"{RED}ERROR: {str}{RESET}")

def warn(str):
    print(f"{YELLOW}WARNING: {str}{RESET}")

def logcmd(str):
    print(f"{BLUE}> {str}{RESET}")

def extract(str,start,stop):
    pos0 = str.find(start)
    pos1 = str.rfind(stop)
    if pos0 == -1 or pos1 == -1 or pos0 == pos1:
        error("could not extract from string \"{str}\"")
        return
    return str[pos0 + 1 : pos1]

def checkOrCreate(path):
    if os.path.exists(path) == False:
        print(f"trying to create output directory {path}")
        os.makedirs(path)
        if os.path.exists(path) == True:
            return True
        error(f"failed to create directory {path}")
        return False
    elif os.path.isfile(path):
        error(f"{path} seems to be a file")
        return False
    
    return True

class Logger:
    def __init__(self, header):
        checkOrCreate(outdir)

        self.isOpen = False

        self.file = None
        self.writer = None

        self.header = header

        self._lock = threading.Lock()

    def open(self, filename):
        with self._lock:
            if self.isOpen:
                self._close_unlocked()

            exists = os.path.exists(filename) and os.path.getsize(filename) > 0

            self.file = open(filename, "a", newline="", encoding="utf-8")
            self.writer = csv.writer(self.file)
            if not exists:
                self.writer.writerow(self.header)
        
            self.isOpen = True

    def close(self):
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self):
        if self.file is not None and not self.file.closed:
            print("closing CSV file")
            self.file.close()
            self.file = None
            self.writer = None
        self.isOpen = False

class EventLogger(Logger):
    def __init__(self):
        super().__init__(["timestamp","datetime","device","event"])

    def write(self, ts, desc, msg):
        with self._lock:
            if self.isOpen:
                print(f"logging: {desc}: {msg}")
                dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')#[:-3]
                self.writer.writerow([ts,dt,desc,msg])
                self.file.flush()
            else:
                warn("no CSV file opened, not writing event")

class MyoLogger(Logger):
    def __init__(self):
        super().__init__([
            "ts-sys", "ts-dev",
            "EMG-ch0", "EMG-ch1", "EMG-ch2", "EMG-ch3", "EMG-ch4", "EMG-ch5", "EMG-ch6", "EMG-ch7",
            # "ORI-w", "ORI-x", "ORI-y", "ORI-z", 
            # "ACC-x", "ACC-y", "ACC-z",
            # "GYRO-x", "GYRO-y", "GYRO-z"
            ])

    def write(self, tsSys, tsDev, values):
        if len(values) != len(self.header) - 2:
            raise RuntimeError(f"number of entries ({len(values)}) does not match number of columns ({len(self.header)-2})")

        with self._lock:
            if self.isOpen:
                self.writer.writerow([tsSys,tsDev,*values])
                self.file.flush()
            else:
                warn("no CSV file opened, not writing event")

class UILogger(Logger):
    def __init__(self):
        super().__init__([
            "ts-sys", "ts-dev",
            "FSR-0", "FSR-1", "FSR-2", "FSR-3",
            "FSR-4", "FSR-5", "FSR-6", "FSR-7",
            "FSR-8", "FSR-9", "FSR-10", "FSR-11"
            ])

    def write(self, tsSys, tsDev, values):
        if len(values) != len(self.header) - 2:
            raise RuntimeError(f"number of entries ({len(values)}) does not match number of columns ({len(self.header)-2})")

        with self._lock:
            if self.isOpen:
                self.writer.writerow([tsSys,tsDev,*values])
                self.file.flush()
            else:
                warn("no CSV file opened, not writing event")

class BoxLogger(Logger):
    def __init__(self):
        super().__init__([
            "ts-sys", "ts-dev",
            "T-0", "P-0", "out-0",
            "T-1", "P-1", "out-1",
            "T-2", "P-2", "out-2",
            "T-3", "P-3", "out-3",
            "T-4", "P-4", "out-4"
            ])

    def write(self, tsSys, tsDev, values):
        if len(values) != len(self.header) - 2:
            raise RuntimeError(f"number of entries ({len(values)}) does not match number of columns ({len(self.header)-2})")

        with self._lock:
            if self.isOpen:
                self.writer.writerow([tsSys,tsDev,*values])
                self.file.flush()
            else:
                warn("no CSV file opened, not writing event")

global logger 
logger = EventLogger()

def log(device,event):
    try:
        if event.find(',') != -1:
            warn(f"string {event} contains comma - replacing by _ for CSV")
            event = event.replace(',','_')
        logger.write(time.time(), device.desc(), event)
    except Exception as e:
        error(f"caught exception during logging: {e}")
