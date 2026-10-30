import os
import re
import csv
import random
import subprocess
from xml.sax.saxutils import escape as xml_escape

sessionName = 'session001'

rootdir = "recordings"
indir = os.path.join(rootdir, sessionName)

outdir = "session_videos"

if not os.path.exists(rootdir):
    print(f"ERROR: root directory '{indir}' does not exist -- exiting script.")
    exit()

if not os.path.exists(indir):
    print(f"ERROR: session directory '{indir}' does not exist -- exiting script.")
    exit()

if not os.path.exists(outdir):
    print(f"output path '{outdir}' does not exist -- creating it")
    os.makedirs(outdir)

chapterFile = sessionName + "-chapters.xml"

### empirically determined delay between audio and video, rooted in audio sample buffer size
### modify as needed
audio_HW_lag = 0.5

### target fps
forceFPS = 15

### output resolution
targetWidth = 1920
targetHeight = 1080

### target video format
forceFormat = 'yuv420p'

### target container
targetExt = ".mkv"

### target video bitrate
videoBitrate = "12M"

# Select one:
# "cpu", "nvidia", "intel", "amd"
encoderType = "cpu"

encoderConfigs = {
    "cpu": {
        "codec": "libx264",
        "preset": "medium",
    },
    "nvidia": {
        "codec": "h264_nvenc",
        "preset": "p4",
    },
    "intel": {
        "codec": "h264_qsv",
        "preset": "medium",
    },
    "amd": {
        "codec": "h264_amf",
        "preset": None,
    },
}

encoderConfig = encoderConfigs[encoderType]
videoCodec = encoderConfig["codec"]
videoPreset = encoderConfig["preset"]

### target audio bitrate
audioBitrate = "192k"

### target audio codec
audioCodec = "aac"

outputFile = sessionName + targetExt


def formatTimeMKV(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    nanoseconds = int(round((seconds - int(seconds)) * 1_000_000_000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{nanoseconds:09d}"


def generateChaptersMKV(inFile, outFile, maxTS):
    rows = []

    with open(os.path.join(inFile), 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["device"].lower() == "marker":
                rows.append(row)

    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Chapters>',
        '  <EditionEntry>'
    ]

    # Generate a random unique 64-bit based ID
    baseID = random.randint(1000000000000000, 8999999999999999)

    for i, row in enumerate(rows):
        relTS = float(row['timestamp']) - maxTS
        # Do not generate invalid negative chapter timestamps.
        if relTS + audio_HW_lag < 0:
            continue
        mkvStartTime = formatTimeMKV(relTS + audio_HW_lag)
        chapterName = xml_escape(row['event'])

        xml.extend([
            f'    <ChapterAtom>',
            f'      <ChapterUID>{baseID + i}</ChapterUID>',
            f'      <ChapterTimeStart>{mkvStartTime}</ChapterTimeStart>',
            f'      <ChapterDisplay>',
            f'        <ChapterString>{chapterName}</ChapterString>',
            f'        <ChapterLanguage>eng</ChapterLanguage>',
            f'      </ChapterDisplay>',
            f'    </ChapterAtom>'
        ])

    xml.extend([
        '  </EditionEntry>',
        '</Chapters>'
    ])

    with open(os.path.join(outFile), 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml))


def getFiles(dir, exts):
    files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

    ret = []
    for f in files:
        baseName, ext = os.path.splitext(f)
        if ext not in exts:
            continue

        subs = f.split('-')
        id = int(subs[1])
        ret.append({"path": f, "offset": 0, "startTS": 0, "label": f"cam{id}", "id": id})

    return ret


### return video files and audio files
def getCaptures(dir):
    vids = getFiles(dir, ['.mkv', '.mp4'])
    auds = getFiles(dir, ['.aac'])

    return [vids, auds]


# NEW: read each user's gesture changes from log.csv and create timed overlays.
def generateGestureFilters(logFile, maxTS):
    gestures = {0: [], 1: [], 2: []}
    eventPattern = re.compile(r'^/user/(power|relax|tripod|pinch)/([012])$')

    with open(logFile, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['device'].lower() != 'marker':
                continue
            match = eventPattern.fullmatch(row['event'].strip())
            if match:
                gesture = match.group(1)
                userID = int(match.group(2))
                # Same timing convention as original MKV chapter generation.
                startTime = float(row['timestamp']) - maxTS + audio_HW_lag
                gestures[userID].append((startTime, gesture))

    # Coordinates: user0 bottom right; user1 top center; user2 bottom left.
    positions = {
        0: ('w-text_w-20', 'h-text_h-20'),
        1: ('(w-text_w)/2', '20'),
        2: ('20', 'h-text_h-20'),
    }

    filters = []
    for userID, events in gestures.items():
        events.sort(key=lambda event: event[0])
        x, y = positions[userID]
        for i, (start, gesture) in enumerate(events):
            end = events[i + 1][0] if i + 1 < len(events) else None
            if end is not None and end <= 0:
                continue
            start = max(0, start)
            if end is not None and end <= start:
                continue

            # Use gte/lt rather than between to avoid an overlap at changes.
            enable = (f"gte(t,{start:.6f})" if end is None
                      else f"gte(t,{start:.6f})*lt(t,{end:.6f})")
            # Escaping the comma in enable is needed by FFmpeg filtergraph parsing.
            enable = enable.replace(',', r'\,')
            filters.append(
                "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':"
                f"text='user{userID}\\:{gesture}':"
                f"x={x}:y={y}:fontsize=36:fontcolor=white:"
                "box=1:boxcolor=black@0.5:"
                f"enable='{enable}'"
            )

    return filters


videos, audios = getCaptures(indir)

# CHANGED: only use cam0 instead of all four cameras.
videos = [v for v in videos if v['id'] == 0]

print("found video files:")
for v in videos:
    print(v['path'])

print("found audio files:")
for a in audios:
    print(a['path'])

if not len(videos) == 1:
    raise Exception(f"expected exactly one cam0 video for '{sessionName}': {len(videos)}")
if not len(audios) == 1:
    raise Exception(f"unexpected number of audios found for '{sessionName}': {len(audios)}")

# only using audio #0
audio = audios[0]

inputs = []
filter_inputs = ""

### extract starting timestamp from ffmpeg stdout dumped into capture logfile
pattern = re.compile(r", start:\s*([\d.]+)")


def extractTS(logfile):
    with open(logfile, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
    return None


### find maximum timestamp (latest time where selected video and audio are capturing)
maxTS = 0
for i, cam in enumerate(videos):
    base_path, ext = os.path.splitext(cam['path'])
    log_path = os.path.join(indir, base_path + ".log")

    ts = extractTS(log_path)
    if ts is None:
        raise Exception(f"start timestamp not found in file '{log_path}'")
    ts += audio_HW_lag

    cam['startTS'] = ts
    maxTS = max(maxTS, ts)
    print(f"v{i}   ts: {ts}")

base_path, ext = os.path.splitext(audio['path'])
log_path = os.path.join(indir, base_path + ".log")

ts = extractTS(log_path)
if ts is None:
    raise Exception(f"start timestamp not found in file '{log_path}'")

audio['startTS'] = ts
maxTS = max(maxTS, ts)

print(f"a    ts: {ts}")
print("-----------------------------")
print(f"max ts: {maxTS}")
print("-----------------------------")

### calculate respective offsets
for i, cam in enumerate(videos):
    cam['offset'] = maxTS - cam['startTS']
    print(f"v{i} offset: {cam['offset']}")
audio['offset'] = maxTS - audio['startTS']
print(f"a  offset: {audio['offset']}")

### specify video input and configure presentation
for i, cam in enumerate(videos):
    inputs.extend(["-ss", f"{cam['offset']:.6f}"])
    path = os.path.join(indir, cam['path'])
    inputs.extend(["-i", path])

    # CHANGED: display the single camera, plus the timed user gestures.
    videoFilters = [
        "scale=interl=0",
        f"format={forceFormat}",
        f"fps={forceFPS}",
        "setpts=PTS-STARTPTS",
        "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':"
        f"text='{cam['label']}':x=20:y=20:fontsize=24:fontcolor=white:"
        "box=1:boxcolor=black@0.5",
        f"scale={targetWidth}:{targetHeight}",
    ]
    videoFilters.extend(generateGestureFilters(os.path.join(indir, 'log.csv'), maxTS))
    filter_inputs += f"[{i}:v]" + ",".join(videoFilters) + "[v0]"

### specify audio input and configure presentation
inputs.extend(["-ss", f"{audio['offset']:.6f}"])
path = os.path.join(indir, audio['path'])
inputs.extend(["-i", path])

### assemble full command line
ffmpeg_cmd = ["ffmpeg", "-hide_banner"]
ffmpeg_cmd.extend(inputs)

audioIndex = len(videos)
ffmpeg_cmd.extend([
    "-filter_complex", filter_inputs,
    "-map", "[v0]",
    "-c:v", videoCodec,
])
if videoPreset is not None:
    ffmpeg_cmd.extend(["-preset", videoPreset])
ffmpeg_cmd.extend([
    "-b:v", videoBitrate,
    "-map", f"{audioIndex}:a",
    "-af", "aresample=async=1:min_hard_comp=0.010000:first_pts=0",
    "-c:a", audioCodec,
    "-b:a", audioBitrate,
    os.path.join(outdir, outputFile)
])

print("Generated Command:\n", " ".join(ffmpeg_cmd))
print("starting encoder")
subprocess.run(ffmpeg_cmd, check=True)
print("encoding done")

print("\ngenerating chapter description file")
generateChaptersMKV(os.path.join(indir, 'log.csv'), os.path.join(outdir, chapterFile), maxTS)

mkvpropedit_cmd = [
    r"C:\Program Files\MKVToolNix\mkvpropedit.exe",
    os.path.join(outdir, outputFile),
    "--chapters", os.path.join(outdir, chapterFile)
]
print("Generated Command:\n", " ".join(mkvpropedit_cmd))
print("injecting chapters")
subprocess.run(mkvpropedit_cmd, check=True)
print("chapter injection done")
