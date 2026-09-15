# StT Video and Audio Capture Script

Python utility for starting and stopping A/V capturing, using the command line tool [ffmpeg](https://ffmpeg.org/), remote-controlled using OSC commands. Furthermore, it serves the purpose of logging further live sensor data and events, both of which are also transmitted via OSC.

## Python Environment

tested with Python 3.10.12

## TODO

- find audio channels associated with video, to capture audio+video from each webcam
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

Run `enumerate.py`, find the device URLs (starting with `@device_`) and paste them into the respective field in `config.json`. IDs are used for the file names and need to be unique for each section. Alternatively, use `ffmpeg -hide_banner -list_devices true -f dshow -i dummy` to list connected devices.

### Output files
Captured files are in format `.mkv` and `.aac`, formatted with `<prefix>-<ID>-<YYYY-MM-DD hh-mm-ss>.<ext>`, where "prefix" is either 'A' for audio devices or 'V' for video devices and ID is the index according to the configuration in (config.json)[./config.json]. Files of each captured session are placed into folders with name specified by the OSC sender, along with `.log` files, which contains the ffmpeg console output. Start and stop times (raw UNIX timestamps as well as formatted) as well as additional data and marker data is written into `log.csv`.

### Starting and stopping recording
send OSC messages `\start` and `\stop` to port 6667:
- *start*: starts capturing on all configured devices and logs actual start time (not time of command reception) to `log.csv`. Argument #1 (type string) specifies the name of the capture session, i.e., the name of the folder containing the recorded files. If capturing was already started, the command is ignored. If capturing is currently shutting down via `\stop` - which causes a slight lag - the command is ignored.
- *stop*: stops capturing on all configured devices and logs actual start time (not time of command reception) to `log.csv`. If capturing was not started via `\start`, the command is ignored. If capturing is currently shutting down via `\stop` - which causes a slight lag - the command is ignored.

### Capture Myo data
send OSC message `/log/myo` to port 6667. 18 arguments of type `float` must be included, in the following order 
- `5x float`: device UNIX timestamp (days, hours, minutes, seconds, milliseconds)
- `5x float`: MCU timestamp (days, hours, minutes, seconds, milliseconds)
- `8x float`: 8-channel Myo EMG data samples
Data will be written into `myo.csv` if recording is in progress, otherwise it will be discarded.

### UI button raw sensor data
send OSC message `/log/ui` to port 6667. 22 arguments of type `float` must be included, in the following order 
- `5x float`: device UNIX timestamp (days, hours, minutes, seconds, milliseconds)
- `5x float`: MCU timestamp (days, hours, minutes, seconds, milliseconds)
- `12x float`: 4-channel FSR samples of 3 user interfaces
Data will be written into `ui.csv` if recording is in progress, otherwise it will be discarded.

### ControlBox data
send OSC message `/log/box/0`, `/log/box/1`, or `/log/box/2` to port 6667, for the respective ControlBox. 25 arguments of type `float` must be included, in the following order 
- `5x float`: device UNIX timestamp (days, hours, minutes, seconds, milliseconds)
- `5x float`: MCU timestamp (days, hours, minutes, seconds, milliseconds)
- `15x float`: 5-part data of 3 ControlBox devices, each of which consisting of `T-0`, `P-0`, `out-0` thru `T-4`, `P-4`, `out-4`, representing target value (`T`), current pressure measurement value (`P`) and PID output control value (`out`) related to each of the 5 involved valve/sensor combinations.
Data will be written into `box-0.csv` thru `box-2.csv` if recording is in progress, otherwise it will be discarded.

### Writing marker events
any other OSC message directed to port 6667 can be used to write custom events (e.g., `/user/pinch/0`), which are written into `log.csv`, along with the current system UNIX timestamp and formatted date/time string. For the value to be written, one argument with non-zero value must be included in the OSC package. 

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
