# utils.py

import os
import csv
import time

from datetime import datetime

# ANSI escape codes for color formatting on console
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

outdir = "L:\\stt"
audioCaptureDir = f'{outdir}\\audio'
videoCaptureDir = f'{outdir}\\video'
snapshotDir = f'{outdir}\\snapshots'

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
        print(f"trying to cerate output directory {path}")
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

    columns = ["timestamp","datetime","device","event"]

    def __init__(self, filename="event-log.csv"):

        path = f"{outdir}\\{filename}"

        exists = os.path.exists(path) and os.path.getsize(path) > 0

        self.file = open(path, "a", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        if not exists:
            # self.writer.writeheader()
            self.writer.writerow(self.columns)

    def write(self, ts, desc, msg):
        print(f"logging: {desc}: {msg}")
        dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self.writer.writerow([ts,dt,desc,msg])
        self.file.flush()

    def close(self):
        if self.file:
            print("closing CSV file")
            self.file.close()

global logger
logger = Logger()

def log(device,event):
    try:
        if event.find(',') != -1:
            warn(f"string {event} contains comma - replacing by _ for CSV")
            event = event.replace(',','_')
        logger.write(time.time(), device.desc(), event)
    except Exception as e:
        error(f"caught exception during logging: {e}")