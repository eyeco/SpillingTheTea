# StT Video and Audio Capture Script

## Python Environment

tested with Python 3.10.12

## TODO

- GUI
- find audio channels associated with video, to capture audio+video from each webcam
- HW-accelerated encoding
- MJPEG/H.264/H.265 streaming from webcam
- check if IDs are conflicting in config.json (e.g., using ID 0 twice)

## How to use
### Configure capture devices
modify `config.json`, which consists of two section, `"video"` and `"audio"`:
```
{
  "video": {
    "0": "@device_..."
    "1": "@device_..."
  },
  "audio": {
    "0": "@device_..."
  }
}
```
each section contains mappings between IDs to device URLs. **Note that URLs are tied to USB ports, so plugging devices to different ports will change the URL descriptions.**

Run `enumerate.py`, find the device URLs (starting with `@device_`) and paste them into the respective field in  `config.json`. IDs are used for the file names and need to be unique for each section. Alternatively, use `ffmpeg -hide_banner -list_devices true -f dshow -i dummy`

### Output files
Captured files are in format `.mp4` and `.aac`, formatted with `<ID>-<prefix>-<YYYY-MM-DD hh-mm-ss.<ext>` and placed into folders `/audio` and `/video`, along with `.log` files, which contains the ffmpeg console output. Start and stop times (raw UNIX timestamps as well as formatted) as well as additional data and marker data is written into `event-log.csv`.

### Starting and stopping recording
send OSC messages `\start` and `\stop` to port 6667:
- *start*: starts capturing on all configured devices and logs actual start time (not time of command reception) to `event-log.csv`. Argument #1 (OSC type `string`) specifies filename *prefix* and can be left blank. If capturing was already started, the command is ignored. If capturing is currently shutting down via `\stop` - which causes a slight lag - the command is ignored.
- *stop*: stops capturing on all configured devices and logs actual start time (not time of command reception) to `event-log.csv`. If capturing was not started via `\start`, the command is ignored. If capturing is currently shutting down via `\stop` - which causes a slight lag - the command is ignored.

### Writing markers
send OSC message `\marker` to port 6667. Arguments are optional and of OSC type `string`. All arguments are joined with a space and written into `event-log.csv`, along with timestamps (raw UNIX timestamps as well as formatted).

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