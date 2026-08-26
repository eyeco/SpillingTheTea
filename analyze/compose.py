import os
import re
import csv
import random
import subprocess

sessionName = 'session003'

rootdir = "L:\\stt"
indir = os.path.join(rootdir,sessionName)

outdir = "L:\\stt"

if not os.path.exists(rootdir):
    print(f"ERROR: root directory '{indir}' does not exist -- exiting script.")
    exit()

if not os.path.exists(indir):
    print(f"ERROR: session directory '{indir}' does not exist -- exiting script.")
    exit()

if not os.path.exists(outdir):
    print(f"output path '{outdir}' does not exist -- creating it")
    os.makedirs(outdir)

#chapterFile = sessionName + "-chapters.txt"
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

### target video codec
# modify according to hardware support
# videoCodec = "libx264"      # libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10  <--- pure software encoder
videoCodec = "h264_nvenc"   # NVIDIA NVENC H.264 encoder
# videoCodec = "h264_qsv"     # H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration)
# videoCodec = "h264_amf"     # AMD AMF H.264 Encoder
# videoCodec = "h264_d3d12va" # D3D12VA h264 encoder

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
        mkvStartTime = formatTimeMKV(relTS + audio_HW_lag)
        chapterName = row['event']
        
        
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
    
    # rite the text strings to file
    with open(os.path.join(outFile), 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml))

def getFiles(dir,exts):

    files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

    ret = []
    for f in files:
        baseName,ext = os.path.splitext(f)
        if not ext in exts:
            continue

        subs = f.split('-')
        #if len(subs) == 3:
            #if not subs[0].lower() == name.lower():
            #    continue

        id = int(subs[1])
        ret.append( {"path": f, "offset": 0, "startTS": 0, "label": f"cam{id}"} )

    return ret

### return all video files and all 
def getCaptures(dir):
    vids = getFiles(dir, ['.mkv', '.mp4'])
    auds = getFiles(dir, ['.aac'])

    return [vids,auds]

videos, audios = getCaptures(indir)

print("found video files:")
for v in videos:
    print( v['path'] )

print("found audio files:")
for a in audios:
    print( a['path'] )

if not len(videos) == 4:
    raise Exception(f"unexpected number of videos found for '{sessionName}': {len(videos)}")
if not len(audios) == 1:
    raise Exception(f"unexpected number of audios found for '{sessionName}': {len(audios)}")

# only using audio #0 (can also multiplex multiple audio streams, if desired -- however, audio for webcams is usually not captured)
audio = audios[0]

inputs = []
filter_inputs = ""

### extract starting timestamp from ffmpeg std output, which was dumped into <capture-file-basename>.log file, 
### placed next to captured file. usually, ts is found in line #3, which looks like this
###   Duration: N/A, start: 1787653884.814912, bitrate: 768 kb/s
###                         ^^^^^^^^^^^^^^^^^
pattern = re.compile(r", start:\s*([\d.]+)")
def extractTS(logfile):
    with open(logfile, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
    return None

### find maximum timestamp (i.e., latest time where all video and audio streams are indeed capturing)
### 1: iterate all video logs
ts = []
maxTS = 0
for i, cam in enumerate(videos):
    base_path,ext = os.path.splitext(cam['path'])
    log_path = os.path.join(indir, base_path + ".log")

    ts = extractTS(log_path) + audio_HW_lag
    if not ts:
        raise Exception(f"start timestamp not found in file '{log_path}'")

    cam['startTS'] = ts
    maxTS = max(maxTS,ts)

    print(f"v{i}   ts: {ts}")

### 2: iterate all audio logs (only one, usually)
base_path,ext = os.path.splitext(audio['path'])
log_path = os.path.join(indir, base_path + ".log")

ts = extractTS(log_path)
if not ts:
    raise Exception(f"start timestamp not found in file '{log_path}'")

audio['startTS'] = ts
maxTS = max(maxTS,ts)


### found max timestamp, used to sync all AV-streams
print(f"a    ts: {ts}")
print("-----------------------------")
print(f"max ts: {maxTS}")
print("-----------------------------")

### calculate respective offsets for all streams
for i, cam in enumerate(videos):
    cam['offset'] = maxTS - cam['startTS']
    print(f"v{i} offset: {cam['offset']}")
audio['offset'] = maxTS - audio['startTS']
print(f"a  offset: {audio['offset']}")

### specify video inputs and configure presentation
for i, cam in enumerate(videos):

    # Use -ss to discard the leading desynced footage per camera
    inputs.extend(["-ss", f"{cam['offset']:.6f}"])

    #specify input
    path = os.path.join(indir, cam['path'])
    inputs.extend(["-i", path])
    
    filter_inputs += (
        # set format, fps, and pts
        f"[{i}:v]scale=interl=0,format={forceFormat},fps={forceFPS},setpts=PTS-STARTPTS,"
        # render text overlays with camera ID at x/y coordinate, with specific text- and background color
        f"drawtext=text='{cam['label']}':x=20:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[v{i}];"
    )

### specify audio input and configure presentation
# use -ss to discard the leading desynced footage
inputs.extend(["-ss", f"{audio['offset']:.6f}"])

#specify input
path = os.path.join(indir, audio['path'])
inputs.extend(["-i", path])

### specify mosaic output for four source videos
layout = "0_0|w0_0|0_h0|w0_h0"
grid_filter = f"[v0][v1][v2][v3]xstack=inputs=4:layout={layout},scale={targetWidth}:{targetHeight}[mosaic]"

### Combine all filter instructions
full_filtergraph = f"{filter_inputs}{grid_filter}"


### assemble full command line
ffmpeg_cmd = [
    "ffmpeg", "-hide_banner"
]

### add inputs
ffmpeg_cmd.extend(inputs)

audioIndex = len(videos)

### add processing instructions
ffmpeg_cmd.extend([
    "-filter_complex", full_filtergraph,

    "-map", "[mosaic]",
    "-c:v", videoCodec,
    "-preset", "p4",
    "-b:v", videoBitrate,

    "-map", f"{audioIndex}:a",
    "-af", "aresample=async=1:min_hard_comp=0.010000:first_pts=0",
    "-c:a", audioCodec,
    "-b:a", audioBitrate,

    os.path.join(outdir, outputFile)
])

### print command line string for manual inspection
print("Generated Command:\n", " ".join(ffmpeg_cmd))

print("starting encoder")
subprocess.run(ffmpeg_cmd)
print("encoding done")


print("\ngenerating chapter description file")

### generating chapter xml from log.csv
generateChaptersMKV(os.path.join(indir,'log.csv'), os.path.join(outdir,chapterFile), maxTS)

### composing command line for adding chapters via mkvpropedit tool
mkvpropedit_cmd = [
    "mkvpropedit", os.path.join(outdir, outputFile), "--chapters", os.path.join(outdir, chapterFile)
]

### print command line string for manual inspection
print("Generated Command:\n", " ".join(mkvpropedit_cmd))

print("injecting chapters")
subprocess.run(mkvpropedit_cmd)
print("chapter injection done")
