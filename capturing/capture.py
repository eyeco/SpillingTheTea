# capture.py

import osc
import utils
import ffmpeg

from audio import AudioDevice
from video import VideoDevice

import os
import json
import time
import atexit
import threading

from pythonosc import dispatcher
from pythonosc.udp_client import SimpleUDPClient

numUsers = 3
oscPortInterface = 6668

def toTimestamp(d,h,m,s,ms):
    return ( ( d * 24 + h ) * 60 + m ) * 60 + s + ms / 1000

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
        if config.audio:
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
        else:
            utils.warn("no audio devices specified")

        self.video = []
        if config.video:
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
        else:
            utils.warn("no video devices specified")

        # print(f"FOUND {len(self.audio)} AUDIO DEVICES:")
        # for i,a in enumerate(self.audio):
        #     print(f"  {i}: {a}")
        # print(f"FOUND {len(self.video)} VIDEO DEVICES:")
        # for i,v in enumerate(self.video):
        #     print(f"  {i}: {v}")

        self.oscClient = SimpleUDPClient("127.0.0.1", oscPortInterface)

        self.lock = (
            threading.Lock()
        )
        self.stopEvent = threading.Event()
        self.pollThread = None

        self.myoLogger = utils.MyoLogger()
        self.uiLogger = utils.UILogger()
        self.boxLoggers = []
        for i in range(numUsers):
            self.boxLoggers.append(utils.BoxLogger())

        self.startPolling()

    def startPolling(self):
        self.stopEvent.clear()
        self.pollThread = threading.Thread(
            target=self.pollLoop, daemon=True
        )
        self.pollThread.start()

    def stopPolling(self):
        self.stopEvent.set()
        if self.pollThread:
            self.pollThread.join()
            self.pollThread = None

    def pollLoop(self):
        print("starting polling")
        while not self.stopEvent.wait(timeout=1.0):

            audAlive = None
            if self.audio != None:
                if len(self.audio) != 0:
                    audAlive = [0] * len(self.audio)
            vidAlive = None
            if self.video != None:
                if len(self.video) != 0:
                    vidAlive = [0] * len(self.video)

            with self.lock:
                for i in range(len(self.audio)):
                    audAlive[i] = self.audio[i].isAlive()
                for i in range(len(self.video)):
                    vidAlive[i] = self.video[i].isAlive()

            if audAlive != None:
                if len(audAlive) != 0:
                    self.oscClient.send_message("/alive/audio", audAlive )
            if vidAlive != None:
                if len(vidAlive) != 0:
                    self.oscClient.send_message("/alive/video", vidAlive )

    def cleanup(self):

        print("stopping polling")
        self.stopPolling()

        print("cleaning up audio devices")
        for a in self.audio:
            a.cleanup()
        print("cleaning up video devices")
        for v in self.video:
            v.cleanup()

        self.myoLogger.close()
        self.uiLogger.close()
        for l in self.boxLoggers:
            l.close()

    def oscStartCapture(self, address, *args):
        if len(args) > 1:
            utils.warn(f"invalid number of arguments in osc {osc.startCommand}: {len(args)}, using first one as name: {args[0]}")

        try:
            name = ""
            if len(args) == 0:
                utils.error(f"argument missing in osc {osc.startCommand}: {len(args)}")
                return
            else:
                name = args[0]
            print(f"OSC: received START capture: {address} (name: \"{name}\")")

            if self.isClosing:
                utils.warn("currently closing, try again later")
                return
            if self.isCapturing:
                utils.warn("already capturing")
                return

            directory = os.path.join(utils.outdir, name)
            utils.checkOrCreate(directory),

            utils.logger.open(os.path.join(directory, "log.csv"))

            self.myoLogger.open(os.path.join(directory, "myo.csv"))
            self.uiLogger.open(os.path.join(directory, "ui.csv"))
            for i in range(len(self.boxLoggers)):
                self.boxLoggers[i].open(os.path.join(directory, f"box-{i}.csv"))

            with self.lock:
                for a in self.audio:
                    a.startCapture(name)
                for v in self.video:
                    v.startCapture(name)
            print(f"started ffmpeg instances for {len(self.audio)} audio and {len(self.video)} video devices")

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

            with self.lock:
                for v in self.video:
                    v.stopCapture()
                for a in self.audio:
                    a.stopCapture()
            print(f"stopped ffmpeg instances for {len(self.audio)} audio and {len(self.video)} video devices")

            utils.logger.close()
            
            self.myoLogger.close()
            self.uiLogger.close()
            for i in range(len(self.boxLoggers)):
                self.boxLoggers[i].close()

            self.isCapturing = False
            self.isClosing = False

        except Exception as e:
            utils.error(f"caught exception in oscStopCapture: \"{e}\"")

    def oscMyoData(self, address, *args):
        try:
            if not self.isCapturing:
                return
            if self.isClosing:
                return

            if len(args) != 5+5+8:  # 5 tsDev + 5 x tsSys + 8-channel EMG
                utils.error(f"invalid number of arguments in myo data ({len(args)})")
                return
            
            if not self.myoLogger.isOpen:
                utils.error("myo logger not opened")
                return

            d0, h0, m0, s0, ms0, d1, h1, m1, s1, ms1, *values = args

            self.myoLogger.write(toTimestamp(d0,h0,m0,s0,ms0), toTimestamp(d1,h1,m1,s1,ms1), values)

        except Exception as e:
            utils.error(f"caught exception in oscMyoData: \"{e}\"")

    def oscUIData(self, address, *args):
        try:
            if not self.isCapturing:
                return
            if self.isClosing:
                return

            if len(args) != 5+5+12:  # 5 x tsDev + 5 x tsSys + 3 x 4 FSR
                utils.error(f"invalid number of arguments in UI data ({len(args)})")
                return
            
            if not self.uiLogger.isOpen:
                utils.error("UI logger not opened")
                return

            d0, h0, m0, s0, ms0, d1, h1, m1, s1, ms1, *values = args

            self.uiLogger.write(toTimestamp(d0,h0,m0,s0,ms0), toTimestamp(d1,h1,m1,s1,ms1), values)

        except Exception as e:
            utils.error(f"caught exception in oscUIData: \"{e}\"")

    def oscBox0Data(self, address, *args):
        try:
            self.onBoxData(0, args)
        except Exception as e:
            utils.error(f"caught exception in oscBox0Data: \"{e}\"")

    def oscBox1Data(self, address, *args):
        try:
            self.onBoxData(1, args)
        except Exception as e:
            utils.error(f"caught exception in oscBox1Data: \"{e}\"")

    def oscBox2Data(self, address, *args):
        try:
            self.onBoxData(2, args)
        except Exception as e:
            utils.error(f"caught exception in oscBox2Data: \"{e}\"")

    def onBoxData(self, userID, args):
        if not self.isCapturing:
            return
        if self.isClosing:
            return

        if len(args) != 5+5+15:  # 5 x tsDev + 5 x tsSys + 5 x 3 PID data
            utils.error(f"invalid number of arguments in box data ({len(args)})")
            return

        l = self.boxLoggers[userID]

        if not l.isOpen:
            utils.error(f"box #{userID} logger not opened")
            return

        d0, h0, m0, s0, ms0, d1, h1, m1, s1, ms1, *values = args

        l.write(toTimestamp(d0,h0,m0,s0,ms0), toTimestamp(d1,h1,m1,s1,ms1), values)

class MarkerManager:

    def oscMarker(self, address, *args):

        if not args or len(args) == 0:
            utils.error(f"argument missing in osc marker")
            return
        if len(args) != 1:
            utils.warn(f"unexpected number of arguments in osc marker: {len(args)}")

        try:
            val = int(args[0])
            
            if val > 0:
                print(f"received marker: {address}")
                utils.log(self, address)

        except (ValueError, TypeError):
            utils.error(f"argument '{args[0]}' is not a valid integer in osc marker (type: {type(args[0]).__name__}).")
            return

    def desc(self):
        return "marker"

# # --- OSC Server Setup ---
capture = CaptureManager()
marker = MarkerManager()
dispatch = dispatcher.Dispatcher()
server = osc.SafeThreadingOSCServer(("127.0.0.1", osc.port), dispatch)


def cleanup():
    capture.cleanup()
    utils.logger.close()

atexit.register(cleanup)

# # Map OSC addresses to the manager functions
dispatch.map(osc.startCommand, capture.oscStartCapture)
dispatch.map(osc.stopCommand, capture.oscStopCapture)

dispatch.map(osc.myoCommand, capture.oscMyoData)
dispatch.map(osc.uiCommand, capture.oscUIData)
dispatch.map(osc.box0Command, capture.oscBox0Data)
dispatch.map(osc.box1Command, capture.oscBox1Data)
dispatch.map(osc.box2Command, capture.oscBox2Data)

dispatch.set_default_handler(marker.oscMarker)


print(f"Listening for OSC on port {osc.port}...")
server.serve_forever()

#v = capture.video[0]
#ffmpeg.snapshot(v, 'test')
#time.sleep(5)