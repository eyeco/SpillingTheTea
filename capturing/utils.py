# utils.py

import os

# ANSI escape codes for color formatting on console
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

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