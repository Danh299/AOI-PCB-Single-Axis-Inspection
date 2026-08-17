# AOI PCBA Single-Axis Inspection System

A PLC-controlled Automated Optical Inspection (AOI) system combining
single-axis motion control, image stitching, and YOLO-based computer
vision for missing-component inspection on PCB assemblies.

<p align="center">
  <img src="images/system_overview.jpg" width="800">
</p>

## Overview

This project was developed as a Mechatronics Engineering capstone project.

The system uses a Mitsubishi FX3U PLC to control a single-axis positioning
stage that moves a PCBA through multiple camera positions. Images captured
at each position are stitched into a higher-resolution PCB image and processed
using a YOLO object detection model to identify electronic components.

The detected component quantities are compared with a reference PCB to
determine whether the inspected board is OK or NG.

A Python/PyQt5 application provides machine control, monitoring, camera
display, inspection results, PLC communication, and data logging.

## Key Features

- Mitsubishi FX3U PLC-based motion control
- Single-axis stepper motor positioning
- PLC-PC communication via Modbus RTU
- Multi-position image acquisition
- PCB image stitching using OpenCV
- YOLO-based electronic component detection
- Reference-based missing-component inspection
- Automatic OK/NG classification
- Manual and Auto operating modes
- Python/PyQt5 monitoring and control GUI
- Inspection data logging and Excel export

## System Architecture

<p align="center">
  <img src="images/system_architecture.png" width="850">
</p>

The PC performs image acquisition, image processing, YOLO inference,
data logging, and operator-interface tasks. The Mitsubishi FX3U PLC
handles machine I/O and stepper motor positioning.

The PLC and PC communicate through Modbus RTU to synchronize motion
and image acquisition.

## System Workflow

1. The operator loads the PCBA onto the fixture.
2. The system performs the homing sequence.
3. The PLC moves the PCBA to predefined inspection positions.
4. The PC captures an image after each positioning-complete signal.
5. Multiple PCB images are stitched into a higher-resolution image.
6. The YOLO model detects and counts electronic components.
7. Detected quantities are compared with the reference PCB.
8. The board is classified as OK or NG.
9. The result and missing components are displayed and stored in the datalog.

## Computer Vision Pipeline

### Multi-Image Acquisition and Stitching

The PCB is captured at multiple positions along the linear axis.
Overlapping images are combined using OpenCV to obtain a larger image
for inspection.

| Single Capture | Stitched PCB |
|---|---|
| ![](images/single_capture.jpg) | ![](images/stitched_image.jpg) |

### Component Detection

The stitched image is processed using a YOLO object detection model
trained to detect PCB components.

<p align="center">
  <img src="images/detection_result.jpg" width="800">
</p>

### Missing-Component Inspection

A reference PCB is first inspected to store the expected number of each
component class.

During normal operation, detected component quantities are compared
against the stored reference.

Example:

Reference:
- LED: 8
- Diode: 8
- IC: 1

Inspected PCB:
- LED: 7
- Diode: 8
- IC: 1

Result:
- Missing LED: 1
- Classification: NG

## Control and Monitoring Software

The machine is controlled through a desktop application developed using
Python and PyQt5.

<p align="center">
  <img src="images/gui.jpg" width="850">
</p>

The software provides:

- Camera monitoring
- Manual JOG and HOME control
- Auto/Manual mode selection
- PLC connection configuration
- Position and velocity configuration
- Reference PCB capture
- OK/NG supervision
- Missing-component display
- Production counters
- Inspection datalog
- Excel export

## Experimental Results

| Metric | Result |
|---|---:|
| Positioning error | ≤ 0.1 mm |
| OK PCB classification | 94% |
| NG PCB classification | 90% |
| Average inspection cycle | ~8.3 s |
| YOLO inference time | ~0.07 s |

<p align="center">
  <img src="images/ok_ng_result.jpg" width="800">
</p>

## Technologies

### Software
- Python
- PyQt5
- OpenCV
- Ultralytics YOLO
- PyModbus
- Pandas

### Automation
- Mitsubishi FX3U PLC
- Modbus RTU
- TB6600 Stepper Driver
- NEMA17 Stepper Motor

### Engineering
- SolidWorks
- AutoCAD Mechanical
- AutoCAD Electrical

## Repository Structure

```text
.
├── src/          # Python application and GUI
├── model/        # Trained YOLO model
├── plc/          # Mitsubishi PLC program
├── images/       # README images and results
├── docs/         # Project documentation
├── demo/         # Demo video information
└── README.md

---

# Installation

Keep it simple:

```markdown
## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/AOI-PCBA-Single-Axis-Inspection.git
cd AOI-PCBA-Single-Axis-Inspection

pip install -r requirements.txt

python src/main.py


Then mention that the physical machine requires:

```markdown
> The complete system requires the Mitsubishi FX3U PLC, camera,
> stepper motor system, and Modbus RTU connection.

## Demo

[Watch the machine demonstration](YOUR_VIDEO_LINK)

## Project Report

The complete capstone report, including mechanical design, electrical
design, control algorithms, computer vision development, and experimental
evaluation, is available here:

[View Full Project Report](docs/AOI_PCBA_Project_Report.pdf)

## Author

**Nguyen Cong Danh**  
Mechatronics Engineering  
HCMUTE

Interests: Computer Vision, Machine Vision, PC Control, Robotics
