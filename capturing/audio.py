# audio.py

import os
import utils
import ffmpeg

import time
import subprocess

class AudioDevice:

    ext = ".aac"

    def __init__(self, id, name, url):
        self.id = id
        self.name = name
        self.url = url

        self.isRecording = False

        self.channels = 1
        self.rate = 48000
        self.bits = 16
        self.bitrate = '192k'


        self.process = None
        self.logFile = None

    def __str__(self):
        #return f"audio #{self.id}: {self.name} ({self.url})"
        return f"audio: {self.name} ({self.url})"
    
    def desc(self):
        return f"A:{self.id}"

    def cleanup(self):
        
        self.stopCapture()

        #paranoia check
        if self.process and self.process.poll() is None:
            utils.warn("terminating ffmpeg process")
            self.process.terminate()
            self.process = None

        if self.logFile:
            self.logFile.close()

    def startCapture(self, name):
        if self.isRecording:
            self.stopCapture()

        timestr = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
        if len(name) > 0:
            filename = f"A-{self.id}-{timestr}{self.ext}"
        else:
            utils.error("name not set for audio")
            return False

        directory = os.path.join(utils.outdir, name)

        print(f"starting capturing {self.name} ({self.url})")
        if ffmpeg.captureAudio(self, directory, filename):
            self.isRecording = True
            utils.log(self, f"start ({filename})")
        else:
            utils.error(f"starting to capture failed {self.name}")

        return self.isRecording

    def stopCapture(self):
        if self.isRecording == False:
            return
        
        print(f"stopping capturing {self.name} ({self.url})")
        utils.log(self, "stop")

        if self.process == None:
            utils.warn(f"capturing process not available")
        else:
            if self.process.poll() is None:
                try:
                    self.process.communicate(input='q', timeout=3) # NOTE: this blocks for 3 seconds, probably not ideal
                except subprocess.TimeoutExpired:
                    # If it doesn't close in 5 seconds, force it
                    utils.error("ffmpeg did not exit on 'q'. Forcing termination...")
                    self.process.kill()
                finally:
                    self.process = None
            else:
                utils.warn("polling failed")
            self.process = None

        if self.logFile:
            self.logFile.close()

        self.isRecording = False

    def isAlive(self):
        if self.isRecording == False:
            return False

        if self.process == None:
            return False
        
        if self.process.poll() is None:
            return True

        return False