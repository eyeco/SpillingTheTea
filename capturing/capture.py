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

oscStartCommand = "/start"
oscStopCommand = "/stop"
oscMarkerCommand = "/marker"

oscPort = 6667

import sys
import traceback
class SafeThreadingOSCServer(osc_server.ThreadingOSCUDPServer):
    def handle_error(self, request, client_address):
        exc_type, exc_value, exc_traceback = sys.exc_info()

        utils.error(f"error while processing OSC data:\n\t{exc_type.__name__ if exc_type else 'Unknown'}\n\tError Message: {exc_value}")

        # utils.error(f"OSC: Caught an issue from {client_address}:\nError Type:    {exc_type.__name__ if exc_type else 'Unknown'}\nError Message: {exc_value}")

        # # 2. OPTIONAL: If it's a completely unexpected error (not the regular expression TypeError),
        # # print the mini stack trace so you can debug your handler functions!
        # if exc_type is not TypeError:
        #     utils.warn("OSC: Unexpected error detected! Printing shorthand stack trace:")
        #     # Prints just the last 2 frames of the track so your console stays tidy
        #     traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2)
        # else:
        #     utils.warn("suppressed expected trailing-byte Type-Mismatch error.")

        pass

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

        self.isClosing = False
        self.isCapturing = False

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
        if len(args) > 1:
            utils.warn(f"invalid number of arguments in osc {oscStartCommand}: {len(args)}, using first one as name: {args[0]}")

        try:
            fileName = ""
            if len(args) == 0:
                utils.warn(f"argument missing in osc {oscStartCommand}: {len(args)} - using blank name")
            else:
                fileName = args[0]
            print(f"OSC: received START capture (name: \"{fileName}\")")


            if self.isClosing:
                utils.warn("currently closing, try again later")
                return
            if self.isCapturing:
                utils.warn("already capturing")
                return

            for v in self.video:
                v.startCapture(fileName)
            for a in self.audio:
                a.startCapture(fileName)

            self.isCapturing = True

        except Exception as e:
            utils.error(f"caught exception in oscStartCapture: \"{e}\"")

    def oscStopCapture(self, address, *args):
        try:
            print(f"OSC: received STOP capture: {address}")

            if not self.isCapturing:
                utils.warn("not currently capturing")
                return
            if self.isClosing:
                utils.warn("closing already in progress")
                return
            
            self.isClosing = True

            for v in self.video:
                v.stopCapture()
            for a in self.audio:
                a.stopCapture()

            self.isCapturing = False
            self.isClosing = False

        except Exception as e:
            utils.error(f"caught exception in oscStopCapture: \"{e}\"")

class MarkerManager:

    def oscMarker(self, address, *args):

        msg = ""
        if len(args) == 0:
            utils.warn(f"no arguments in {oscMarkerCommand}: {len(args)}")
            msg = "<empty>"
        else:
            msg = " ".join(args)
        
        print(f"received marker: {msg}")

        if not capture.isCapturing:
            utils.warn("received trigger while capturing")

        utils.log(self, msg)

    def desc(self):
        return "marker"

# # --- OSC Server Setup ---
capture = CaptureManager()
marker = MarkerManager()
dispatch = dispatcher.Dispatcher()
# server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", oscPort), dispatch)
server = SafeThreadingOSCServer(("127.0.0.1", oscPort), dispatch)

def cleanup():
    capture.cleanup()
    utils.logger.close()

atexit.register(cleanup)

# # Map OSC addresses to the manager functions
dispatch.map(oscStartCommand, capture.oscStartCapture)
dispatch.map(oscStopCommand, capture.oscStopCapture)
dispatch.map(oscMarkerCommand, marker.oscMarker)

print(f"Listening for OSC on port {oscPort}...")
server.serve_forever()

# if manager.video[0].startCapture("test") == True:
#     time.sleep(3)
#     manager.video[0].stopCapture()

# if manager.audio[0].startCapture("test") == True:
#     time.sleep(3)
#     manager.audio[0].stopCapture()


# v = manager.video[0].startCapture()
# a = manager.audio[0].startCapture()
# time.sleep(3)
# if v:
#     manager.video[0].stopCapture()
# if a:
#     manager.audio[0].stopCapture()
