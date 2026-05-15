# capture.py

import utils
import ffmpeg

from audio import AudioDevice
from video import VideoDevice

import os
import json
import time
import atexit

from pythonosc import osc_server
from pythonosc import dispatcher

class Config:

    def __init__(self):
        config = self.load()

        self.audio = None
        self.video = None

        audioCfg = config["audio"]
        if not audioCfg:
            utils.warn("audio configuration missing")
        else:
            self.audio = audioCfg

        videoCfg = config["video"]
        if not videoCfg:
            utils.warn("video configuration missing")
        else:
            self.video = videoCfg

    def getAudioID(self, url):

        for id in self.audio:
            if self.audio[id] == url:
                return id
        return None
    
    def getAudioURL(self, id):

        if self.audio:
            try:
                return self.audio[f"{id}"]
            except KeyError:
                return None
        return None

    def getVideoID(self, url):

        for id in self.video:
            if self.video[id] == url:
                return id
        return None
    
    def getVideoURL(self, id):

        if self.video:
            try:
                return self.video[f"{id}"]
            except KeyError:
                return None
        return None

    def load(self, path=".\\config.json"):
        if not os.path.exists(path):
            utils.error(f"configuration file missing: {path}")
            return None

        with open(path, "r", encoding="utf-8") as f:
            dict = json.load(f)
            return dict


class CaptureManager:
    def __init__(self):

        config = Config()

        lines = ffmpeg.enum()

        foundAudio = {}
        foundVideo = {}

        for i in range(len(lines)):
            l = lines[i]
            if(l.lower().find("(audio)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = utils.extract(l,'"','"')
                    url = utils.extract(lines[i+1],'"','"')

                    foundAudio[url] = name
                else:
                    utils.error(f"could not find alternative name of audio device {l}")

            if(l.lower().find("(video)") != -1):
                if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
                    name = utils.extract(l,'"','"')
                    url = utils.extract(lines[i+1],'"','"')

                    foundVideo[url] = name
                else:
                    utils.error(f"could not find alternative name of video device {l}")

        print("found audio devices:")
        for a in foundAudio:
            print(f"- {foundAudio[a]} ({a})")
        print("found video devices:")
        for v in foundVideo:
            print(f"- {foundVideo[v]} ({v})")

        self.audio = []
        for a in config.audio:
            url = config.audio[a]
            try:
                device = foundAudio[url]
            except KeyError:
                device = None
            if device:
                print(f"creating audio device ID: {a}, name: {device}, url: {url}")
                self.audio.append(AudioDevice(a, device, url))
            else:
                utils.error(f"audio device not available: {a} ({url})")

        self.video = []
        for v in config.video:
            url = config.video[v]
            try:
                device = foundVideo[url]
            except KeyError:
                device = None
            if device:
                print(f"creating video device ID: {v}, name: {device}, url: {url}")
                self.video.append(VideoDevice(v, device, url))
            else:
                utils.error(f"video device not available: {v} ({url})")

        # print(f"FOUND {len(self.audio)} AUDIO DEVICES:")
        # for i,a in enumerate(self.audio):
        #     print(f"  {i}: {a}")
        # print(f"FOUND {len(self.video)} VIDEO DEVICES:")
        # for i,v in enumerate(self.video):
        #     print(f"  {i}: {v}")

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
# dispatch = dispatcher.Dispatcher()

# utils.checkOrCreate(AudioDevice.captureDir)
# utils.checkOrCreate(VideoDevice.captureDir)

# def cleanup():
#     manager.cleanup()

# atexit.register(cleanup)

# # # Map OSC addresses to the manager functions
# dispatch.map("/study/start", manager.oscStartCapture)
# dispatch.map("/study/stop", manager.oscStopCapture)

# server = osc_server.BlockingOSCUDPServer(("127.0.0.1", 5005), dispatch)
# print("Listening for OSC on port 5005...")
# server.serve_forever()

# if manager.video[0].startCapture("test") == True:
#     time.sleep(3)
#     manager.video[0].stopCapture()

# if manager.audio[0].startCapture("test") == True:
#     time.sleep(3)
#     manager.audio[0].stopCapture()

