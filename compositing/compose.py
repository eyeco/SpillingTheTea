import subprocess
import os
import re

indir = "L:\\stt"
audioCaptureDir = f'{indir}\\audio'
videoCaptureDir = f'{indir}\\video'

outdir = "L:\\stt"

setName = 'test2'
chapter_source = "chapters.txt"

audio_HW_lag = 0.5

video_target = setName + "-synced.mp4"

# videos = [
#     {"path": "0--2026-06-29 13-27-14.mp4", "offset": 0, "startTS": 0, "label": "cam0"},
#     {"path": "1--2026-06-29 13-27-14.mp4", "offset": 0, "startTS": 0, "label": "cam1"},
#     {"path": "2--2026-06-29 13-27-15.mp4", "offset": 0, "startTS": 0, "label": "cam2"},
#     {"path": "3--2026-06-29 13-27-15.mp4", "offset": 0, "startTS": 0, "label": "cam3"}
# ]

# audio = {"path": "0--2026-06-29 13-27-15.aac", "offset": 0, "startTS": 0}

def getFiles(name,dir,exts):

    files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

    ret = []
    for f in files:
        baseName,ext = os.path.splitext(f)
        if not ext in exts:
            continue

        subs = f.split('--')
        if len(subs) == 3:
            if not subs[0].lower() == name.lower():
                continue

            id = int(subs[1])
            ret.append( {"path": f, "offset": 0, "startTS": 0, "label": f"cam{id}"} )

    return ret

def getCaptures(name):

    vids = getFiles(name,videoCaptureDir, ['.mkv', '.mp4'])
    auds = getFiles(name,audioCaptureDir, ['.aac'])

    return [vids,auds]

videos, audios = getCaptures(setName)

for v in videos:
    print( v['path'] )
for a in audios:
    print( a['path'] )


if not len(videos) == 4:
    raise Exception(f"unexpected number of videos found for '{setName}': {len(videos)}")
if not len(audios) == 1:
    raise Exception(f"unexpected number of audios found for '{setName}': {len(audios)}")

audio = audios[0]

inputs = []
filter_inputs = ""

def extractTS(logfile):
    with open(logfile, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
    return None

ts = []
maxTS = 0
pattern = re.compile(r", start:\s*([\d.]+)")
for i, cam in enumerate(videos):
    base_path,ext = os.path.splitext(cam['path'])
    log_path = os.path.join(videoCaptureDir, base_path + ".log")

    ts = extractTS(log_path) + audio_HW_lag
    if not ts:
        raise Exception(f"start timestamp not found in file '{log_path}'")

    cam['startTS'] = ts
    maxTS = max(maxTS,ts)

    print(f"v{i}   ts: {ts}")

base_path,ext = os.path.splitext(audio['path'])
log_path = os.path.join(audioCaptureDir, base_path + ".log")

ts = extractTS(log_path)
if not ts:
    raise Exception(f"start timestamp not found in file '{log_path}'")

audio['startTS'] = ts
maxTS = max(maxTS,ts)

print(f"a    ts: {ts}")
print("-----------------------------")
print(f"max ts: {maxTS}")
print("-----------------------------")

for i, cam in enumerate(videos):
    cam['offset'] = maxTS - cam['startTS']
    print(f"v{i} offset: {cam['offset']}")

audio['offset'] = maxTS - audio['startTS']
print(f"a  offset: {audio['offset']}")

forceFPS = 15
forceFormat = 'yuv420p'

for i, cam in enumerate(videos):
    # Use -ss to discard the leading desynced footage per camera
    path = os.path.join(videoCaptureDir, cam['path'])
    inputs.extend(["-ss", f"{cam['offset']:.6f}"])
    inputs.extend(["-i", path])
    
    # Apply time-base correction and burn text labels onto each input channel
    filter_inputs += (
        f"[{i}:v]scale=interl=0,format={forceFormat},fps={forceFPS},setpts=PTS-STARTPTS,"
        f"drawtext=text='{cam['label']}':x=20:y=20:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[v{i}];"
    )

path = os.path.join(audioCaptureDir, audio['path'])
inputs.extend(["-ss", f"{audio['offset']:.6f}"])
inputs.extend(["-i", path])

targetWidth = 1920
targetHeight = 1080

# Position matrix for 1280x720 source videos
layout = "0_0|w0_0|0_h0|w0_h0"
grid_filter = f"[v0][v1][v2][v3]xstack=inputs=4:layout={layout},scale={targetWidth}:{targetHeight}[mosaic]"

# Combine all filter instructions together
full_filtergraph = f"{filter_inputs}{grid_filter}"

# --- 4. ASSEMBLE FULL COMMAND ---
ffmpeg_cmd = [
    "ffmpeg", "-hide_banner"
]

# Add our shifted inputs
ffmpeg_cmd.extend(inputs)

audioIndex = len(videos)

# Add processing instructions and point to our GPU encoder
ffmpeg_cmd.extend([
    "-filter_complex", full_filtergraph,

    "-map", "[mosaic]",
    "-c:v", "h264_nvenc",
    "-preset", "p4",
    "-b:v", "12M",

    "-map", f"{audioIndex}:a",
    "-af", "aresample=async=1:min_hard_comp=0.010000:first_pts=0",
    "-c:a", "aac",
    "-b:a", "192k",

    os.path.join(outdir, video_target)
])

#print("\n\r".join(ffmpeg_cmd))

# Print out the command line string for manual inspection
print("Generated Command:\n", " ".join(ffmpeg_cmd))

subprocess.run(ffmpeg_cmd)