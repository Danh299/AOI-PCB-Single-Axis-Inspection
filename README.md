# README.md

# AOI PCBA Single-Axis Inspection System

A single-axis **Automated Optical Inspection (AOI)** system for PCBA missing-component inspection, integrating **Mitsubishi FX3U PLC motion control, OpenCV image stitching, YOLO-based computer vision, Modbus RTU communication, and a Python/PyQt5 control application**.

<p align="center">
  <img src="images/system_overview.jpg" width="850" alt="AOI PCBA Inspection System">
</p>

---

## Overview

This project was developed as a **Mechatronics Engineering capstone project** to design and implement an automated PCBA inspection system using machine vision.

A Mitsubishi FX3U PLC controls a single-axis positioning stage driven by a stepper motor. The PCBA is moved through multiple predefined camera positions, where individual images are captured.

The captured images are stitched using OpenCV to generate a larger PCB image with improved visual detail. A trained YOLO object detection model then identifies and counts electronic components on the PCBA.

During normal inspection, the detected component quantities are compared with data obtained from a reference PCB. The inspected board is automatically classified as **OK** or **NG**, and missing components are reported.

A Python/PyQt5 desktop application provides machine control, real-time monitoring, camera display, PLC communication, reference capture, inspection results, production counters, and data logging.

---

## Key Features

* Mitsubishi FX3U PLC-based machine control
* Single-axis stepper motor positioning
* PLC-PC communication via Modbus RTU
* Manual and automatic operation modes
* Multi-position image acquisition
* High-resolution PCB image reconstruction using OpenCV image stitching
* YOLO-based electronic component detection
* Reference-based component comparison
* Automatic PCBA OK/NG classification
* Missing-component identification
* PCB orientation checking using detected Header position
* Python/PyQt5 machine-control interface
* Real-time camera and system monitoring
* Inspection counters and datalog
* Excel report export
* Configurable positioning and velocity parameters

---

## System Architecture

<p align="center">
  <img src="images/system_architecture.png" width="850" alt="System Architecture">
</p>

The system is divided into two main control layers:

### PC Layer

The PC performs:

* Camera acquisition
* Image stitching
* YOLO inference
* Component counting
* Reference comparison
* OK/NG decision making
* Operator interface
* Data logging
* Excel report generation

### PLC Layer

The Mitsubishi FX3U PLC performs:

* Stepper motor positioning
* Homing
* JOG control
* Sensor monitoring
* Limit-switch monitoring
* Lighting control
* Machine sequence control
* Status signaling

The PC and PLC communicate through **Modbus RTU** to synchronize motion, camera acquisition, and inspection processing.

```text
┌────────────────────────── PC Application ──────────────────────────┐
│                                                                   │
│  PyQt5 GUI                                                        │
│      │                                                            │
│      ├── Camera Acquisition                                       │
│      │        ↓                                                   │
│      ├── Multi-Position Images                                    │
│      │        ↓                                                   │
│      ├── OpenCV Image Stitching                                   │
│      │        ↓                                                   │
│      ├── YOLO Component Detection                                 │
│      │        ↓                                                   │
│      ├── Component Counting                                       │
│      │        ↓                                                   │
│      ├── Reference Comparison                                     │
│      │        ↓                                                   │
│      └── OK / NG + Datalog                                        │
│                                                                   │
│                     Modbus RTU                                    │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
                    Mitsubishi FX3U PLC
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        Stepper Driver    Sensors      Indicators
              │
              ▼
         NEMA17 Motor
              │
              ▼
       Single-Axis Stage
```

---

## System Workflow

1. The operator loads the PCBA onto the fixture.
2. The system performs the homing sequence.
3. The PLC moves the PCBA to a predefined inspection position.
4. The PC receives the positioning-complete signal through Modbus RTU.
5. The camera captures the PCB image at the current position.
6. The PLC moves to the next inspection position.
7. Steps 3–6 repeat until all required images are captured.
8. OpenCV stitches the captured images into one larger PCB image.
9. The YOLO model detects and counts electronic components.
10. The detected quantities are compared with the stored reference PCB.
11. The PCBA is classified as **OK** or **NG**.
12. Missing components are displayed for NG boards.
13. Inspection results are stored in the datalog.
14. The positioning stage returns to its home position.

```text
PCBA Loading
     │
     ▼
   Homing
     │
     ▼
PLC Positioning
     │
     ▼
Camera Capture
     │
     ▼
Next Position?
 ┌───┴────┐
Yes       No
 │         │
 └────────►▼
     Image Stitching
          │
          ▼
     YOLO Detection
          │
          ▼
    Component Counting
          │
          ▼
   Reference Comparison
          │
          ▼
       OK / NG
          │
          ▼
        Datalog
```

---

# Computer Vision Pipeline

## Multi-Image Acquisition and Stitching

A single camera image may not provide sufficient visual detail for small PCB components.

The PCBA is therefore moved along the linear axis and captured at several overlapping positions.

OpenCV is used to stitch the individual images into a larger PCB image before component detection.

| Single Camera Capture                             | Stitched PCB Image                                |
| ------------------------------------------------- | ------------------------------------------------- |
| <img src="images/single_capture.jpg" width="420"> | <img src="images/stitched_image.jpg" width="420"> |

The application uses OpenCV's scan-mode image stitcher:

```python
self.imageStitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
self.imageStitcher.setWaveCorrection(False)
```

The stitched image is also checked against a minimum expected width to detect incomplete stitching.

---

## YOLO Component Detection

The stitched PCB image is processed using an **Ultralytics YOLO object detection model**.

<p align="center">
  <img src="images/detection_result.jpg" width="850" alt="YOLO Component Detection">
</p>

The detector identifies multiple electronic component classes, including:

* LED
* Diode
* 7-Segment Display
* Button
* Header
* IC
* SMD Resistor
* SMD Capacitor
* SMD LED

Inference is performed on the stitched PCB image:

```python
results = self.yolo_model.predict(
    imgin,
    conf=MIN_CONF_THRESH,
    iou=0.4,
    imgsz=960
)
```

Per-class confidence thresholds are also applied to filter low-confidence detections.

---

## PCB Orientation Checking

The system additionally checks whether the PCB has been loaded in the correct orientation.

The detected **Header** component is used as an orientation reference.

```text
Header on left side
        ↓
Correct PCB orientation

Header on right side
        ↓
PCB upside down
```

If the Header is missing or detected on the incorrect side, the inspection process reports an error instead of generating a normal OK/NG result.

---

## Reference-Based Missing-Component Inspection

Before normal production inspection, a complete reference PCB is inspected using **Reference Capture** mode.

The system stores the expected number of components for each detected class.

Example reference:

```text
LED       : 8
Diode     : 8
7_Seg     : 8
Button    : 8
Header    : 1
IC        : 1
Res_SMD   : 4
Cap_SMD   : 2
LED_SMD   : 1
```

During normal inspection, the detected component quantities are compared against the stored reference.

### Example

**Reference PCB**

```text
LED    : 8
Diode  : 8
IC     : 1
```

**Inspected PCB**

```text
LED    : 7
Diode  : 8
IC     : 1
```

**Inspection Result**

```text
Missing Component:
LED : 1

Classification:
NG
```

If all required component quantities match the reference, the board is classified as:

```text
OK
```

Otherwise:

```text
NG
```

and the missing components are displayed.

---

# PLC-PC Communication

Communication between the PC application and Mitsubishi FX3U PLC is implemented using **Modbus RTU**.

The Python application uses `pymodbus` to establish the serial connection.

```python
self.client = ModbusSerialClient(
    port=self.port,
    stopbits=1,
    bytesize=8,
    parity='E',
    baudrate=int(self.baud_rate),
    timeout=2.0
)

self.client.connect()
```

The PC continuously exchanges control and status registers with the PLC.

### Communication Functions

The Modbus register system is used for:

* Auto/Manual mode selection
* START/STOP control
* JOG control
* Homing
* Lighting control
* OK/NG signals
* Ready status
* Position-complete status
* Position-processing status
* Sensor monitoring
* Current position
* Target position
* Positioning parameters
* Velocity parameters

---

## Motion and Camera Synchronization

The PLC-PC communication provides a handshake between the positioning system and camera.

```text
PLC moves PCBA
      │
      ▼
Position reached
      │
      ▼
PLC sets Position Complete
      │
      ▼
PC detects signal
      │
      ▼
Camera captures image
      │
      ▼
PC sends Position Start
      │
      ▼
PLC moves to next position
```

When the final position is completed, the PC automatically starts the image-stitching and YOLO inspection process.

---

# Control and Monitoring Software

The machine is operated through a desktop application developed using **Python and PyQt5**.

<p align="center">
  <img src="images/gui.jpg" width="900" alt="PyQt5 Control Interface">
</p>

The GUI contains four main sections.

## Camera View

Provides:

* Real-time camera display
* Processed PCB image
* Detection result
* OK/NG supervision
* Production counters
* Machine control

---

## System View

Provides:

* Machine visualization
* Sensor monitoring
* Limit-switch monitoring
* Current position
* Target position
* Position configuration
* Velocity configuration
* JOG control
* HOME control
* Lighting control

---

## Image Setup

Used for reference-PCB configuration.

Functions include:

* Reference Capture
* Reference component display
* Reference component storage

Reference data is saved in JSON format and can be reloaded when the application is restarted.

---

## Datalog

Stores inspection information including:

* Inspection number
* OK/NG status
* Missing components
* Inspection timestamp

Inspection records can be exported directly to an Excel file.

---

# Operating Modes

## Manual Mode

Manual mode is intended for machine setup and maintenance.

Available controls include:

* JOG+
* JOG-
* HOME
* Lighting control
* Position configuration
* Velocity configuration
* Position data transfer to PLC

---

## Auto Mode

Auto mode performs the complete automated inspection cycle.

Two operations are available.

### Normal Inspection

```text
Positioning
   ↓
Image Capture
   ↓
Stitching
   ↓
Detection
   ↓
Reference Comparison
   ↓
OK / NG
   ↓
Datalog
```

### Reference Capture

Used to inspect a complete PCB and save its component quantities as the reference for future inspections.

---

# Experimental Results

The completed prototype was evaluated in terms of positioning accuracy, component inspection performance, and processing time.

| Metric                         |   Result |
| ------------------------------ | -------: |
| Positioning error              | ≤ 0.1 mm |
| OK PCB classification accuracy |      94% |
| NG PCB classification accuracy |      90% |
| Average inspection cycle       |   ~8.3 s |
| Image stitching time           |   ~1.0 s |
| YOLO inference time            |  ~0.07 s |

<p align="center">
  <img src="images/ok_ng_result.jpg" width="850" alt="OK and NG Inspection Results">
</p>

The NG test PCB contained deliberately removed components to evaluate the missing-component inspection capability.

---

# Mechanical Design

The mechanical system was designed using **SolidWorks** and consists of:

* Aluminum extrusion frame
* Single-axis linear positioning mechanism
* T8 lead screw
* NEMA17 stepper motor
* Linear guide shafts
* PCB fixture
* Camera mounting structure
* Lighting system

<p align="center">
  <img src="images/cad_design.png" width="800" alt="Mechanical CAD Design">
</p>

The final prototype was fabricated based on the mechanical design.

---

# Electrical System

The electrical system includes:

* Mitsubishi FX3U PLC
* 24 VDC power supply
* TB6600 stepper driver
* NEMA17 stepper motor
* PCB presence sensor
* Homing sensor
* Mechanical limit switches
* LED illumination system
* OK/NG/Ready indicators
* RS-485 communication interface

Electrical schematics were designed using **AutoCAD Electrical**.

---

# Technologies

## Computer Vision

* OpenCV
* Ultralytics YOLO
* Object Detection
* Image Stitching
* Image Processing

## Programming

* Python
* PyQt5
* Pandas
* JSON

## Industrial Communication

* Modbus RTU
* RS-485
* PyModbus

## Automation

* Mitsubishi FX3U PLC
* GX Works2
* Stepper Motor Positioning
* TB6600 Stepper Driver
* NEMA17 Stepper Motor

## Engineering Design

* SolidWorks
* AutoCAD Mechanical
* AutoCAD Electrical

---

# Repository Structure

```text
AOI-PCBA-Single-Axis-Inspection/
│
├── README.md
├── requirements.txt
│
├── src/
│   ├── main.py
│   ├── connection_dialog.py
│   ├── ui_main.py
│   └── ui_connection_dialog.py
│
├── model/
│   └── README.md
│
├── plc/
│   ├── PLC_program/
│   ├── ladder_screenshots/
│   └── README.md
│
├── images/
│   ├── system_overview.jpg
│   ├── system_architecture.png
│   ├── cad_design.png
│   ├── single_capture.jpg
│   ├── stitched_image.jpg
│   ├── detection_result.jpg
│   ├── ok_ng_result.jpg
│   └── gui.jpg
│
├── docs/
│   └── AOI_PCBA_Project_Report.pdf
│
├── demo/
│   └── README.md
│
└── config/
    ├── reference_component_data.json
    └── positioning_example.json
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/AOI-PCBA-Single-Axis-Inspection.git
cd AOI-PCBA-Single-Axis-Inspection
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Main Python dependencies include:

```text
PyQt5
ultralytics
opencv-python
pymodbus
pandas
openpyxl
```

## 3. Add the Trained YOLO Model

Place the trained model inside the model directory.

```text
model/
└── best.pt
```

Update the model path in the application if necessary.

Example:

```python
self.yolo_model = YOLO("model/best.pt")
```

## 4. Connect the Hardware

The complete system requires:

* Mitsubishi FX3U PLC
* USB camera
* RS-485 communication adapter
* TB6600 stepper driver
* NEMA17 stepper motor
* Sensors and limit switches
* 24 VDC power supply

## 5. Configure Modbus RTU

Select the appropriate:

* COM port
* Baud rate

from the connection configuration window.

## 6. Run the Application

```bash
python src/main.py
```

> **Note:** The software can be opened without the complete machine, but full inspection and motion-control functionality requires the physical PLC, camera, positioning system, and Modbus RTU connection.

---

# Demo

A demonstration video of the complete AOI system can be viewed here:

**[Watch the Machine Demonstration](YOUR_VIDEO_LINK)**

The demonstration includes:

1. Machine startup
2. PLC-PC connection
3. Homing
4. Automatic positioning
5. Multi-position image capture
6. Image stitching
7. YOLO component detection
8. OK PCB inspection
9. NG PCB inspection
10. Missing-component reporting

---

# Project Report

The complete Mechatronics Engineering capstone report contains detailed information about:

* System concept and design
* Mechanical calculations
* Mechanical CAD design
* Electrical system design
* PLC control
* Modbus RTU communication
* Image-processing algorithms
* YOLO training
* PyQt5 GUI development
* Experimental testing
* Performance evaluation

**[View Full Project Report](docs/AOI_PCBA_Project_Report.pdf)**

---

# Future Improvements

Potential improvements include:

* Upgrade from single-axis to two-axis positioning
* Use an industrial camera with higher resolution
* Improve illumination uniformity
* Detect additional PCB defect types
* Detect component misalignment and wrong orientation
* Detect soldering defects
* Increase the PCB dataset size
* Improve image-stitching robustness
* Optimize inspection-cycle time
* Deploy the inspection system for larger and more complex PCB assemblies

---

# Author

**Nguyen Cong Danh**

Mechatronics Engineering
HCMUTE

**Areas of Interest**

* Computer Vision
* Machine Vision
* PC Control
* Robotics
* AI for Industrial Inspection
