# capture.py

import utils
import ffmpeg

from audio import AudioDevice
from video import VideoDevice

import time
import atexit

from pythonosc import osc_server
from pythonosc import dispatcher


class CaptureManager:
    def __init__(self):
        self.audio = []
        self.video = []

        lines = ffmpeg.enum()

        for i in range(len(lines)):
            l = lines[i]
            if(l.lower().find("(audio)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = utils.extract(l,'"','"')
                    url = utils.extract(lines[i+1],'"','"')
                    self.audio.append(AudioDevice(i,name,url))
                else:
                    utils.error(f"could not find alternative name of audio device {l}")
                

            if(l.lower().find("(video)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = utils.extract(l,'"','"')
                    url = utils.extract(lines[i+1],'"','"')
                    self.video.append(VideoDevice(i,name,url))
                else:
                    utils.error(f"could not find alternative name of video device {l}")

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

utils.checkOrCreate(AudioDevice.captureDir)
utils.checkOrCreate(VideoDevice.captureDir)

def cleanup():
    manager.cleanup()

atexit.register(cleanup)

# # # Map OSC addresses to the manager functions
# dispatch.map("/study/start", manager.oscStartCapture)
# dispatch.map("/study/stop", manager.oscStopCapture)

# server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 5005), dispatch)
# print("Listening for OSC on port 5005...")
# server.serve_forever()

if manager.video[0].startCapture("test") == True:
    time.sleep(3)
    manager.video[0].stopCapture()

if manager.audio[0].startCapture("test") == True:
    time.sleep(3)
    manager.audio[0].stopCapture()
