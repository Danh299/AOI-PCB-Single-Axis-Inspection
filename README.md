# AOI-PCB-Single-Axis-Inspection
Project Description

This project presents the design and development of a single-axis Automated Optical Inspection (AOI) system for PCBA inspection. A Mitsubishi FX3U PLC controls a stepper-driven linear positioning stage to move the PCB through multiple camera positions. Images captured at each position are stitched into a higher-resolution PCB image and processed using a trained YOLO11 object detection model to identify electronic components and detect missing-component defects.

A Python/PyQt5 application provides machine control, real-time monitoring, image processing, inspection results, and data logging. Communication between the PC and PLC is implemented through Modbus RTU, enabling synchronized motion and image acquisition.

The prototype supports Manual and Auto operation, reference-PCB capture, automatic OK/NG classification, missing-component reporting, and inspection-data export.
