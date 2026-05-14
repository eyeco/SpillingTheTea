# import pyaudio
# import sounddevice as sd
# from pygrabber.dshow_graph import FilterGraph

# fg  = FilterGraph
# p = pyaudio.PyAudio()

# def enumVideo(fg):
#     devices = fg.get_input_devices()

#     print(f"video devices:")
#     for index, name in enumerate(devices):
#         print(f"Index {index}: {name}")
#     print(f"\n\n")

# def enumAudio(p):
#     info = p.get_host_api_info_by_index(0)
#     num_devices = info.get('deviceCount')

#     print(f"audio devices:")
#     for i in range(0, num_devices):
#         device = p.get_device_info_by_host_api_device_index(0, i)
#         if device.get('maxInputChannels') > 0:
#             print(f"Audio Input ID {i}: {device.get('name')}")
#     print(f"\n\n")

# enumVideo(fg)
# enumAudio(p)

import os
import time
import atexit
import subprocess

from pythonosc import osc_server
from pythonosc import dispatcher


captureDirAudio = 'L:\\stt\\audio'
captureDirVideo = 'L:\\stt\\video'

RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def error(str):
    print(f"{RED}ERROR: {str}{RESET}")

def warn(str):
    print(f"{YELLOW}WARNING: {str}{RESET}")

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

def extract(str,start,stop):
    pos0 = str.find(start)
    pos1 = str.rfind(stop)
    if pos0 == -1 or pos1 == -1 or pos0 == pos1:
        error("could not extract from string \"{str}\"")
        return
    return str[pos0 + 1 : pos1]


class AudioDevice:
    def __init__(self, id, name, url):
        #self.id = id
        self.name = name
        self.url = url

        self.isRecording = False

        self.process = None

    def __str__(self):
        #return f"audio #{self.id}: {self.name} ({self.url})"
        return f"audio: {self.name} ({self.url})"
    
    def cleanup(self):
        
        self.stopCapture()

        #paranoia check
        if self.process and self.process.poll() is None:
            warn("terminating ffmpeg process")
            self.process.terminate()
            self.process = None
            
    def startCapture(self, filename):
        if self.isRecording:
            self.stopCapture()

        return self.isRecording

    def stopCapture(self):
        if self.isRecording == False:
            return

        self.isRecording = False

class VideoDevice:
    def __init__(self, id, name, url):
        #self.id = id
        self.name = name    # friendly name (not unique)
        self.url = url      # NOTE: this is a unique identifier, however it also includes the USB port, so when you re-plug to different USB ports, the ids change!

        self.isRecording = False
        self.supportsMJPEG = self.checkMJPEG()

        self.process = None
        self.logFile = None

    def __str__(self):
        #return f"video #{self.id}: {self.name} ({self.url})"
        return f"video: {self.name} ({self.url})"

    def cleanup(self):
        
        self.stopCapture()

        #paranoia check
        if self.process and self.process.poll() is None:
            warn("terminating ffmpeg process")
            self.process.terminate()
            self.process = None

        if self.logFile:
            self.logFile.close()

    def startCapture(self, name):
        if self.isRecording:
            self.stopCapture()

        print(f"starting capturing {self.name} ({self.url})")

        timestr = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
        filename = f"{name}-{timestr}.mp4"

        if ffmpeg.run(self, filename, True):
            self.isRecording = True
        else:
            error(f"starting to capture failed {self.name}")

        return self.isRecording

    def stopCapture(self):
        if self.isRecording == False:
            return
            
        print(f"stopping capturing {self.name} ({self.url})")

        if self.process == None:
            warn(f"capturing process not available")
        else:
            if self.process.poll() is None:
                try:
                    self.process.communicate(input='q', timeout=3) # NOTE: this blocks for 3 seconds, probably not ideal
                except subprocess.TimeoutExpired:
                    # If it doesn't close in 5 seconds, force it
                    error("ffmpeg did not exit on 'q'. Forcing termination...")
                    self.process.kill()
                finally:
                    self.process = None
            else:
                warn("polling failed")
            self.process = None

        if self.logFile:
            self.logFile.close()

        self.isRecording = False

    def checkMJPEG(self):
        lines = ffmpeg.options(self)
        print(f"checking for MJPEG support ({self.url})")
        for l in lines:
            l = l.lstrip()
            if l.find("pixel_format=") or l.find("vcodec="):
                if l.find("mjpeg") != -1 or l.find("mjpg") != -1 or l.find("motion_j_p_e_g") != -1:
                    print("MJPEG SUPPORTED")
                    return True
        warn(f"MJEPG NOT SUPPORTED ({self.name})")
        return False

class ffmpeg:
    def enum():
        cmd = [
            'ffmpeg', '-hide_banner',
            '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'
        ]

        print(f"> {' '.join(cmd)}")

        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode < 0:
            error(f"returned with error code {result.returncode}")
        output = result.stderr
        lines = output.split('\n')

        return lines
    
    def options(device):
        cmd = [
            'ffmpeg', '-hide_banner',
            '-f', 'dshow', '-list_options', 'true', '-i', f'video={device.name}'
        ]
        print(f"> {' '.join(cmd)}")

        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        if result.returncode < 0:
            error(f"returned with error code {result.returncode}")
        output = result.stderr
        lines = output.split('\n')

        return lines
    
    def run(device, filename, tryMJPEG):
        pathVid = os.path.join(captureDirVideo, filename)
        pathLog = os.path.splitext(pathVid)[0] + ".log"

        if os.path.exists(pathVid):
            error(f"file {filename} already exists in {captureDirVideo} - will not overwrite")
            return False

        print(f"starting to record file {pathVid}")

        format = 'yuyv422'
        if tryMJPEG == True and device.supportsMJPEG == True:
            format = 'mjpeg'
        cmd = [
            'ffmpeg', '-hide_banner',
            '-f', 'dshow', 
            '-use_wallclock_as_timestamps', '1',
            '-pixel_format', format, # Try this if -vcodec fails
            '-i', f'video={device.url}',
            #'-c:v', 'libx264', '-preset', 'veryfast', 
            #'-c:a', 'aac',
            pathVid
        ]
        print(f"> {' '.join(cmd)}")

        # result = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        # if result.returncode < 0:
        #     error(f"returned with error code {result.returncode}")
        # output = result.stderr
        # lines = output.split('\n')

        # for l in lines:
        #     print(l)

        process = None

        try:
            logFile = open(pathLog, "w")
            process = subprocess.Popen(cmd, stderr=logFile, stdin=subprocess.PIPE, text=True)
            #process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self.logFile, text=True)
        except FileNotFoundError:
            error("FFmpeg was not found. Is it installed and in your PATH?")
        except OSError as e:
            error(f"Failed to launch process: {e}")

        device.process = process
        device.logFile = logFile

        return True


# if video[0].startCapture("test") == True:
#     time.sleep(3)
#     video[0].stopCapture()

# import subprocess
# import os

class CaptureManager:
    def __init__(self):
        self.audio = []
        self.video = []

        lines = ffmpeg.enum()

        for i in range(len(lines)):
            l = lines[i]
            if(l.lower().find("(audio)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = extract(l,'"','"')
                    url = extract(lines[i+1],'"','"')
                    self.audio.append(AudioDevice(i,name,url))
                else:
                    error(f"could not find alternative name of audio device {l}")
                

            if(l.lower().find("(video)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = extract(l,'"','"')
                    url = extract(lines[i+1],'"','"')
                    self.video.append(VideoDevice(i,name,url))
                else:
                    error(f"could not find alternative name of video device {l}")

        print(f"FOUND {len(self.audio)} AUDIO DEVICES:")
        for i,a in enumerate(self.audio):
            print(f"  {i}: {a}")
        print(f"FOUND {len(self.video)} VIDEO DEVICES:")
        for i,v in enumerate(self.video):
            print(f"  {i}: {v}")

    def cleanup(self):
        print("cleaning up audio devices")
        for a in self.audio:
            a.cleanup()
        print("cleaning up video devices")
        for v in self.video:
            v.cleanup()

    def oscStartCapture(self, address, *args):
        deviceID = args[0]
        fileName = args[1]

        print(f"OSC: received START capture ({deviceID}, {fileName})")

    def oscStopCapture(self, address, *args):
        deviceID = args[0]
        fileName = args[1]

        print(f"OSC: received STOP capture ({deviceID}, {fileName})")


# # --- OSC Server Setup ---
manager = CaptureManager()
dispatch = dispatcher.Dispatcher()

checkOrCreate(captureDirAudio)
checkOrCreate(captureDirVideo)

def cleanup():
    manager.cleanup()

atexit.register(cleanup)

# # Map OSC addresses to the manager functions
dispatch.map("/study/start", manager.oscStartCapture)
dispatch.map("/study/stop", manager.oscStopCapture)

server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 5005), dispatch)
print("Listening for OSC on port 5005...")
server.serve_forever()
