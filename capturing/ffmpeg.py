# ffmpeg.py

import utils

import os
import subprocess
import datetime
from pathlib import Path

def enum():
    cmd = [
        'ffmpeg', '-hide_banner',
        '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'
    ]
    utils.logcmd(f"{' '.join(cmd)}")

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if result.returncode < 0:
        utils.error(f"returned with error code {result.returncode}")
    output = result.stderr
    lines = output.split('\n')

    return lines

def audioOptions(url):
    cmd = [
        'ffmpeg', '-hide_banner',
        '-f', 'dshow', '-list_options', 'true', '-i', f'audio={url}'
    ]
    utils.logcmd(f"{' '.join(cmd)}")

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if result.returncode < 0:
        utils.error(f"returned with error code {result.returncode}")
    output = result.stderr
    lines = output.split('\n')

    return lines

def videoOptions(url):
    cmd = [
        'ffmpeg', '-hide_banner',
        '-f', 'dshow', '-list_options', 'true', '-i', f'video={url}'
    ]
    utils.logcmd(f"{' '.join(cmd)}")

    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    if result.returncode < 0:
        utils.error(f"returned with error code {result.returncode}")
    output = result.stderr
    lines = output.split('\n')

    return lines

def captureAudio(device, directory, filename):

    utils.checkOrCreate(directory)

    pathAud = os.path.join(directory, filename)
    pathLog = os.path.splitext(pathAud)[0] + ".log"

    if os.path.exists(pathAud):
        utils.error(f"file {filename} already exists in {directory} - will not overwrite")
        return False
    
    print(f"starting to record file {pathAud}")

    initial_timecode = datetime.datetime.now().strftime("%H:%M:%S:00")

    cmd = [
        'ffmpeg', '-hide_banner',
        '-f', 'dshow', 
        '-use_wallclock_as_timestamps', '1',

        '-channels', f'{device.channels}',
        '-sample_rate', f'{device.rate}',
        '-sample_size', f'{device.bits}',

        '-i', f'audio={device.url}',

        #'-af', 'aresample=async=1:first_pts=0',
        '-async', '1',              # prevent timestamp drifting

        '-flush_packets', '1',      # don't buffer, bypass windows cache

        '-c:a', 'aac',

        '-b:a', device.bitrate,

        "-timecode", initial_timecode,

        pathAud
    ]
    utils.logcmd(f"{' '.join(cmd)}")

    process = None

    try:
        logFile = open(pathLog, "w")
        process = subprocess.Popen(cmd, stderr=logFile, stdin=subprocess.PIPE, text=True)
        #process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self.logFile, text=True)
    except FileNotFoundError:
        utils.error("FFmpeg was not found. Is it installed and in your PATH?")
    except OSError as e:
        utils.error(f"Failed to launch process: {e}")

    device.process = process
    device.logFile = logFile

    return True

def snapshot(device, filename):

    utils.checkOrCreate(utils.snapshotDir)

    if not filename.lower().endswith('.jpg') and not filename.lower().endswith('.jpeg'):
        path = Path(filename)
        newname = str(path.with_suffix('.jpg'))
        utils.warn(f"file {filename} will be modified to {newname} - only jpeg supported")
        filename = newname

    pathPic = os.path.join(utils.snapshotDir, filename)
    pathLog = os.path.splitext(pathPic)[0] + ".log"

    if os.path.exists(pathPic):
        utils.error(f"file {filename} already exists in {utils.snapshotDir} - will not overwrite")
        return False
    
    print(f"saving snapshot to file {pathPic}")

    cmd = [
        'ffmpeg', '-hide_banner',
        '-y', # overwrite
        '-f', 'dshow',
        '-video_size', '1280x720',
        '-i', f'video={device.url}', 
        '-ss', '00:00:01',
        '-vframes', '1',
        '-q:v', '2', 
        pathPic
    ]

    utils.logcmd(f"{' '.join(cmd)}")

    process = None

    try:
        logFile = open(pathLog, "w")
        process = subprocess.Popen(cmd, stderr=logFile, stdin=subprocess.PIPE, text=True)
        #process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self.logFile, text=True)
    except FileNotFoundError:
        utils.error("FFmpeg was not found. Is it installed and in your PATH?")
    except OSError as e:
        utils.error(f"Failed to launch process: {e}")

    device.process = process
    device.logFile = logFile

    return True

def captureVideo(device, directory, filename, tryMJPEG):

    utils.checkOrCreate(directory)

    pathVid = os.path.join(directory, filename)
    pathLog = os.path.splitext(pathVid)[0] + ".log"

    if os.path.exists(pathVid):
        utils.error(f"file {filename} already exists in {directory} - will not overwrite")
        return False

    print(f"starting to record file {pathVid}")

    initial_timecode = datetime.datetime.now().strftime("%H:%M:%S:00")

    option = '-pixel_format'
    value = 'yuyv422'
    if tryMJPEG == True and device.supportsMJPEG == True:
        option = '-vcodec'
        value = 'mjpeg'
    cmd = [
        'ffmpeg', '-hide_banner',
        '-f', 'dshow', 
        '-use_wallclock_as_timestamps', '1',

        option, value, 
        '-video_size', f'{device.width}x{device.height}',
        '-framerate', f'{device.fps}',

        '-i', f'video={device.url}',

        '-flush_packets', '1',      # don't buffer, bypass windows cache

        #'-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',   # H.264 very fast
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',  # H.264 ultra fast
        '-b:v', device.bitrate,

        #'-c:v', 'copy',     #write directly to disc

        #'-c:a', 'aac',

        "-timecode", initial_timecode,

        pathVid
    ]
    utils.logcmd(f"{' '.join(cmd)}")

    process = None

    try:
        logFile = open(pathLog, "w")
        process = subprocess.Popen(cmd, stderr=logFile, stdin=subprocess.PIPE, text=True)
        #process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=self.logFile, text=True)
    except FileNotFoundError:
        utils.error("FFmpeg was not found. Is it installed and in your PATH?")
    except OSError as e:
        utils.error(f"Failed to launch process: {e}")

    device.process = process
    device.logFile = logFile

    return True
