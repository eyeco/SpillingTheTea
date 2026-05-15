# StT Video and Audio Capture Script

## Python Environment

tested with Python 3.10.12

## TODO

- read camera/mic association from config-file
- control start/stop (and file names?) from OSC interface
- write metadata to CSV
- log exact start time of each stream recording
- find audio channels associated with video, to capture audio+video from each webcam
- HW-accelerated encoding
- MJPEG streaming from webcam

## Dependencies

### ffmpeg 
[download link](https://ffmpeg.org/download.html)

tested with 8.1.1 for Windows:
```
ffmpeg version 8.1.1-essentials_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers
  built with gcc 15.2.0 (Rev13, Built by MSYS2 project)
```

### Python packages
```
pip install pythonosc
```