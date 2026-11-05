# SpillingTheTea

Software repository for LIT Robopsychology Lab installation [Spilling the Tea](https://www.jku.at/en/ars-electronica-2026-future-begins-negotiating-humanity/spilling-the-tea-a-soft-material-experience/), created for the Ars Electronica Festival 2026.

## Content

### Sample code for analysis of captured data

Sample Python scripts for A/V data compositing and sample Jupyter notebook demonstrating basic data handling for analysis of captured `CSV` files. For more details see content of the [analyze](./analyze/) folder.

### Button UI

Python code for UI remote control. For details see the according [README](./buttonInterface/README.md) file.

### Scripts for A/V capturing

Python code for A/V setup and capturing. For details see the according [README](./capturing/README.md) file.

### MCU firmware for physical button interfaces and control-box

Arduino firmware code for physical button interface (see [README](./firmware/button-interface/README.md)) and for control-box (see [README](./firmware/control-box-serial/README.md)), including serial communication with sqıd.

### sqıd visual programming environment + scene files

Precompiled binaries of sqıd tool. See the [project repository](https://github.com/eyeco/sqid) for details.

## Author

Roland Aigner [[link](https://www.rolandaigner.com)]

## License

sqıd Visual Programming Environment is licensed under the GPL3 License. See the sqıd project [LICENSE](https://github.com/eyeco/sqid/blob/main/LICENSE) file (also contained in the [precompiled package](./sqid/sqid.zip)) for more information.

All other content of this package is licensed under the Polyform 1.0.0 License. See [LICENSE](./LICENSE) file in the package root for more information.