# enumerate.py

import utils
import ffmpeg

audio = []
audioURL = []
video = []
videoURL = []

lines = ffmpeg.enum()

for i in range(len(lines)):
    l = lines[i]
    if(l.lower().find("(audio)") != -1):
        if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
            audio.append( utils.extract(l,'"','"') )
            audioURL.append( utils.extract(lines[i+1],'"','"') )
        else:
            utils.error(f"could not find alternative name of audio device {l}")

    if(l.lower().find("(video)") != -1):
        if i + 1 < len(lines) and lines[i+1].lower().find("Alternative name"):
            video.append( utils.extract(l,'"','"') )
            videoURL.append( utils.extract(lines[i+1],'"','"') )
        else:
            utils.error(f"could not find alternative name of video device {l}")

print("audio devices:")
for a,url in zip(audio,audioURL):
    lines = ffmpeg.audioOptions(url)
    print(f"\t{a} ({url})")
    print(f"\t\tformats:")
    for l in lines:
        ch = l.find("ch=")
        bits = l.find("bits=")
        rate = l.find("rate=")
        if ch != -1 and bits != -1 and rate != -1:
            print(f"\t\t{l[ch:]}")
            # subs = l[ch:].split(',')
            # ch = (int)(subs[0].strip()[3:])
            # bits = (int)(subs[1].strip()[5:])
            # rate = (int)(subs[2].strip()[5:])
            # print(f"\t\tchannels {ch} sample bits {bits:2} sample rate {rate:5}")

print("video devices:")
for v,url in zip(video,videoURL):
    lines = ffmpeg.videoOptions(url)
    print(f"\t{v} ({url})")
    print(f"\t\tformats:")
    for l in lines:
        px = l.find("pixel_format=")
        min = l.find("min")
        max = l.find("max")
        if px != -1 and min != -1 and max != -1:
            print(f"\t\t{l[px:]}")
    print(f"\t\tcodecs:")
    for l in lines:
        cd = l.find("vcodec=")
        min = l.find("min")
        max = l.find("max")
        if cd != -1 and min != -1 and max != -1:
            print(f"\t\t{l[cd:]}")
