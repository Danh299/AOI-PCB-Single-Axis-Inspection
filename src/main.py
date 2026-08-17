# PyQt5 Libraries
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QMessageBox, QTableWidgetItem)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtGui import QColor, QFont

# Built-in Libraries
from ultralytics import YOLO 
from datetime import datetime
import cv2
from pymodbus.client import ModbusSerialClient
import pandas as pd
import json

import time

# My Libraries
from connection_dialog import Ui_ConnectionDialog_Class
from ui_main import Ui_MainWindow

# Background Color SheetStyle
BG_GREEN        = "background-color: hsl(120,255,200)"
BG_YELLOW       = "background-color: hsl(60,255, 200)"          
BG_RED          = "background-color: hsl(0,255,200)"
BG_WHITE        = "background-color: hsl(0,0,255)"
BG_BLUE         = "background-color: hsl(200,255,200)"
BG_DARK_RED     = "background-color: hsl(0,255,150)"
BG_DARK_GREEN   = "background-color: hsl(120,255,100)"

# Memory Control Register Bit D100 (Write Only)
# | 0           | 0                 | 0              | 0                 |
# | 0           | 0                 | 0              | 0                 |
# | 0           | 0                 | 0              | Ready Control     |
# | Pos Start   | NG Control        | OK Control     | Auto/Man Control  |

MMR_CTRL_REG        = 100

MMR_CTRL_AUTO_MAN   = 0
MMR_CTRL_OK         = 1
MMR_CTRL_NG         = 2
MMR_CTRL_POS_START  = 3
MMR_CTRL_READY      = 4

# Device Control Register Bit D101 (Write Only)
# | 0              | 0            | 0               | 0                 |
# | 0              | 0            | 0               | 0                 |
# | 0              | 0            | SW Stop Button  | SW Start Button   |
# | Homing Control | Jog- Control | Jog+ Control    | Light Control     |

DEV_CTRL_REG        = 101

DEV_CTRL_LIGHT      = 0
DEV_CTRL_JOG_FOR    = 1
DEV_CTRL_JOG_REV    = 2
DEV_CTRL_HOMING     = 3
DEV_CTRL_SW_START   = 4
DEV_CTRL_SW_STOP    = 5

# Memory Status Register Bit D102 (Read Only)
# | 0               | 0             | 0                 | 0                 |
# | 0               | 0             | 0                 | Ready Status      |
# | Pos Processing  | Pos Clear     | Pos Complete      | Busy              |
# | NG Status       | OK Status     | Auto/Man Status   | Start/Stop Status |

MMR_STAT_REG        = 102

MMR_STAT_START_STOP = 0
MMR_STAT_AUTO_MAN   = 1
MMR_STAT_OK         = 2
MMR_STAT_NG         = 3
MMR_STAT_BUSY       = 4
MMR_STAT_POS_CPLT   = 5
MMR_STAT_POS_CLEAR  = 6
MMR_STAT_POS_PROC   = 7 
MMR_STAT_READY      = 8

# Device Status Register Bit D103 (Read Only)
# | 0             | 0           | 0           | 0            |
# | 0             | 0           | Reversed    | Forward      |
# | DOG           | SS PCB      | LS-         | LS+          | 
# | Homing Status | Jog- Status | Jog+ Status | Light Status |

DEV_STAT_REG        = 103

DEV_STAT_LIGHT      = 0
DEV_STAT_JOG_FOR    = 1
DEV_STAT_JOG_REV    = 2
DEV_STAT_HOMING     = 3
DEV_STAT_LS_FOR     = 4
DEV_STAT_LS_REV     = 5
DEV_STAT_SS_PCB     = 6
DEV_STAT_DOG        = 7
DEV_STAT_FOR        = 8
DEV_STAT_REV        = 9

# Current Position Registers    D104-105
CUR_POS_REG         = 104
        
# Target Position Registers     D106-107
TARGET_POS_REG      = 106
        
# Setting Velocity Registers    D150-D154
SET_VEL_REG         = 150
        
# Position Data Registers       D(200 + 2 * n) (0 <= n <= 4)
POS1_DATA_REG       = 200

# Number of Positioning
POS_NUM_REG         = 0

# Confidence Thresholds for each PCB Components
CONF_THRESH = {
    "LED":      0.65,
    "7_Seg":    0.65,
    "Button":   0.65,
    "IC":       0.65,
    "Header":   0.65,
    "Diode":    0.65,
    "Cap_SMD":  0.65,
    "Res_SMD":  0.65,
    "LED_SMD":  0.5,
}

MIN_CONF_THRESH = 0.65

# Stepper motor parameter limits
MAX_POS_VALUE = 5000000
MAX_VEL_VALUE = 10000
MAX_POS_NUM   = 10

# Minimum Stitched image width size (check for insufficient stitching images)
MIN_STITCHED_IMG_W = 900

class DetectionWorker(QThread):
    result_ready = pyqtSignal(dict)
    
    def __init__(self, images, stitcher, yolo_model):
        super().__init__()
        self.images = images
        self.sticher = stitcher
        self.yolo_model = yolo_model
       
    def run(self):    
        print("Begin Running") 
        data = {}
        data["ImageOut"], data["ObjectDict"], data["Error"] = None, None, ""
        
        start = time.perf_counter()
        imgin, stitch_error = self.stitch_image()
        end = time.perf_counter()
        print(f"Stitching took {end - start:.4f} seconds")
        
        if imgin is not None:
            start = time.perf_counter()
            data["ImageOut"], data["ObjectDict"], header_pos = self.detect_object_yolo(imgin)
            end = time.perf_counter()
            print(f"Detection took {end - start:.4f} seconds")
            
            # Check if PCB is upside down
            if header_pos == "right":
                data["Error"] = "PCB is upside down"
            elif header_pos == "absent":
                data["Error"] = "No header detected"
                
        elif stitch_error == "small_width":
            data["Error"] = "Stitching error: Small stitched image width"
        elif stitch_error == "error_stitch":
            data["Error"] = "Stitching error: Can't stitch images"

        self.result_ready.emit(data)

    def stitch_image(self):
        print(len(self.images))
        for i in range(len(self.images)):
            cv2.imwrite("Img_" + str(i) + ".jpg", self.images[i])
        error, stitched_img = self.sticher.stitch(self.images)
        
        if not error:
            stitched_img = cv2.copyMakeBorder(stitched_img, 10, 10, 10, 10, cv2.BORDER_CONSTANT, (0,0,0))
            cv2.imwrite("Img_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".jpg", stitched_img)
            _, w = stitched_img.shape[:2]
            print(w)
            if w >= MIN_STITCHED_IMG_W:
                print("STITCHED!")
                return stitched_img, ""
            else:
                print("STITCH small!")
                return None, "small_width"
        else:
            print("STITCH error!")
            return None, "error_stitch"
        
    def detect_object_yolo(self, imgin):
        
        # Declaration
        imgout = imgin.copy()
        imgout = cv2.cvtColor(imgout, cv2.COLOR_BGR2RGB)
        names = self.yolo_model.names
        obj_dic = {}
        obj_conf_sum = {}
        header_pos = ""

        # Predict objects in image and get detection information
        results = self.yolo_model.predict(imgin, conf = MIN_CONF_THRESH, iou = 0.4, imgsz = 960)
        boxes = results[0].boxes.xyxy.cpu()
        clss = results[0].boxes.cls.cpu().tolist()
        confs = results[0].boxes.conf.tolist() 

        # Draw boxes, classes, confidence on output image
        for box, cls, conf in zip(boxes, clss, confs):
            label = names[int(cls)]
            
            # If confidence of object doesn't pass threshold, ignore (default value is 0.5)
            if conf < CONF_THRESH.get(label, 0.5):
                continue
            
            # Draw boxes
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(imgout, (x1, y1), (x2, y2), (255, 255, 0), 2)
            text = f"{label} {conf:.2f}"
            cv2.putText(imgout, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            obj_dic[label] = obj_dic.get(label, 0) + 1          # Store detection result on dictionary
            obj_conf_sum[label] = obj_conf_sum.get(label, 0) + conf
        
        # Print confidence of object detection
        obj_avg_conf = {
            label: obj_conf_sum[label] / obj_dic[label]
            for label in obj_dic
        }
        print(str(obj_avg_conf))
        
        # Check if PCB is upside down
        if label == "Header":
            x_center = (x1 + x2) / 2
            _, w, _ = imgout.shape
            header_pos = "left" if x_center < w / 2 else "right"
        
        if "Header" not in obj_dic:
            header_pos = "absent"
        
        print(header_pos)
            
        return imgout, obj_dic, header_pos

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.baud = "9600"
        self.port = "COM7"
        
    def pass_connection_param(self, port, baud):
        self.baud = baud
        self.port = port
        
class Ui_MainWindow_Class(Ui_MainWindow):
    
    # Initialize MainWindow and its UI
    def __init__(self, MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        self.setupUi(self.MainWindow)
        self.modifyUI()
        MainWindow.show()
        
    # Added function calls to Ui
    def modifyUI(self):
                        
        # Control/Status variables
        self.cam_open_state         = True        # Camera status
        self.man_mode               = False       # True if Manual mode, otherwise Auto mode
        self.start_state            = False       # True if system is open
        self.connection_state       = False       # True if connected to PLC
        self.system_busy_state      = False

        # Detection and Positioning signal
        self.captured_img_signal    = True
        self.detected_img_signal    = False
        self.pos_processing         = False
        
        ### Modbus register variables (PLC Devices) ###
            
        # Memory Control Register D100 (Write Only) 
        self.mmr_ctrl_reg = 0
        
        # Device Control Register Bit D101 (Write Only)     
        self.dev_ctrl_reg = 0
        
        # Memory Status Register Bit D102 (Read Only)   
        self.mmr_stat_reg = 0
            
        # Device Status Register Bit D103 (Read Only) 
        self.dev_stat_reg = 0
           
        # Current Position Registers D104-105 
        self.cur_pos_val = 0
         
        # Position Data Registers D(200 + 2 * n) (0 <= n <= 4)              
        self.pos_data_regs = [0] * (10 * 2)
            
        # Test time duration for one system cycle
        self.start_time = 0
        self.end_time = 0    
        self.run_start_time = 0
        self.run_end_time = 0
        
        # PCB OK/NG Counts on normal operations
        self.ok_count       = 0
        self.ng_count       = 0
            
        # Other variables
        self.video_capture  = 1     # 0 for laptop camera, 1 for webcam
        self.data_log_index = 0     # Current index in datalog table
        self.current_page   = 0
        self.auto_mode_op   = 1     # 1 For Normal operation, 2 for Reference capture
        self.frame          = None
        
        # YOLO Model
        self.yolo_model = YOLO("yolov8n_model.pt")
        
        # Image stitcher
        self.imageStitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
        self.imageStitcher.setWaveCorrection(False)
        
        self.captured_images = []
        
        # Dictionary storing PCB components information
        self.reference_comp_dict    = {}
        self.detected_comp_dict     = {}
        self.missing_comp_dict      = {}
        
        # Datalog Column Width Sizing
        self.table_log.setColumnWidth(0, 70)        # Index (STT)
        self.table_log.setColumnWidth(1, 100)       # OK/NG
        self.table_log.setColumnWidth(2, 500)       # Missing components      
        self.table_log.setColumnWidth(3, 400)       # Time
        font = QFont("Cambria Math", 12)
        font.setBold(True)
        self.table_log.setFont(font)
        
        # Positioning and Detection Data Loading
        self.load_pos_table()
        self.load_ref_data()
        self.table_pos.setColumnWidth(0, 70)       # Index (STT)
        self.table_pos.setColumnWidth(1, 70)       # Position
        font = QFont("Cambria Math", 12)
        font.setBold(True)
        self.table_pos.setFont(font)
        
        # Scale taken picture to fill the screen
        self.lb_cam.setScaledContents(True)
        self.lb_detect.setScaledContents(True)
        
        # Timer1 for capturing picture
        self.timer1 = QTimer()
        self.timer1.timeout.connect(lambda: self.update_frame())
        self.timer1.stop()
        
        # Timer for Modbus communication (Read value)
        self.timer2 = QTimer()
        self.timer2.timeout.connect(lambda: self.receive_messenge())
        self.timer2.stop()
        
        ### Button functions ###
        
        # Control panel buttons
        self.but_ctl_cam_off.clicked.connect(lambda: self.control_cam(False))
        self.but_ctl_cam_on.clicked.connect(lambda: self.control_cam(True))
        self.but_ctl_mode_auto.clicked.connect(lambda: self.control_auto_man(False))
        self.but_ctl_mode_man.clicked.connect(lambda: self.control_auto_man(True))
        self.but_ctl_dis.clicked.connect(lambda: self.control_connection(False))
        self.but_ctl_con.clicked.connect(lambda: self.control_connection(True))
        self.but_ctl_start.pressed.connect(lambda: self.control_start_stop_press(True , auto_mode_op = 1))
        self.but_ctl_stop.pressed.connect(lambda: self.control_start_stop_press(False))
        self.but_ctl_start.released.connect(lambda: self.control_start_stop_release(True))
        self.but_ctl_stop.released.connect(lambda: self.control_start_stop_release(False))
        
        # Image setup buttons
        self.but_img_ref.pressed.connect(lambda: self.control_start_stop_press(True , auto_mode_op = 2))
        self.but_img_stop.pressed.connect(lambda: self.control_start_stop_press(False))
        self.but_img_ref.released.connect(lambda: self.control_start_stop_release(True))
        self.but_img_stop.released.connect(lambda: self.control_start_stop_release(False))
        self.but_save_detection.clicked.connect(lambda: self.save_ref_data())
        
        # Manual mode system control
        self.but_view_light.clicked.connect(lambda: self.manual_control("LIGHT"))
        self.but_view_jog_for.pressed.connect(lambda: self.manual_control("JOG+ ON"))
        self.but_view_jog_rev.pressed.connect(lambda: self.manual_control("JOG- ON"))
        self.but_view_jog_for.released.connect(lambda: self.manual_control("JOG+ OFF"))
        self.but_view_jog_rev.released.connect(lambda: self.manual_control("JOG- OFF"))
        self.but_view_home.clicked.connect(lambda: self.manual_control("HOME"))
        self.but_man_ctrl_jog_for.pressed.connect(lambda: self.manual_control("JOG+ ON"))
        self.but_man_ctrl_jog_rev.pressed.connect(lambda: self.manual_control("JOG- ON"))
        self.but_man_ctrl_jog_for.released.connect(lambda: self.manual_control("JOG+ OFF"))
        self.but_man_ctrl_jog_rev.released.connect(lambda: self.manual_control("JOG- OFF"))
        self.but_man_ctrl_home.clicked.connect(lambda: self.manual_control("HOME"))

        self.but_view_pos_save.clicked.connect(lambda: self.save_pos_table())
        self.but_view_pos_send.clicked.connect(lambda: self.send_motor_param_data())
        
        # Page switch buttons
        self.but_side_cam.clicked.connect(lambda: self.switch_to_camera_view())
        self.but_side_view.clicked.connect(lambda: self.switch_to_system_view())
        self.but_side_setup.clicked.connect(lambda: self.switch_to_img_setup())
        self.but_side_log.clicked.connect(lambda: self.switch_to_datalog())
        
        # Other buttons
        self.but_side_con.clicked.connect(lambda: self.show_connection_dialog())
        self.but_log_export.clicked.connect(lambda: self.export_to_excel())
        self.but_log_delete.clicked.connect(lambda: self.delete_table())
        self.but_sup_reset.clicked.connect(lambda: self.reset_count())

#####################################################################################
#################################### CONTROL PANEL ##################################       
#####################################################################################

    # Camera control
    def control_cam(self, open_cam):
        
        # Camera is open when open_cam is True, otherwise closed
        if open_cam:
            try:
                self.cap = cv2.VideoCapture(self.video_capture)
            except Exception as e:
                QMessageBox.critical(self.MainWindow, "Camera Error", f"{e}")
                return
            self.timer1.start(100)
            self.cam_open_state = True
            self.button_change_after_selection(self.but_ctl_cam_on, BG_GREEN, self.but_ctl_cam_off, BG_WHITE)
        else:
            self.timer1.stop()
            self.lb_cam.clear()
            self.cap.release() 
            self.cam_open_state = False
            self.button_change_after_selection(self.but_ctl_cam_off, BG_RED, self.but_ctl_cam_on, BG_WHITE) 
        
    # Auto/Man control
    def control_auto_man(self, set_man_mode):
        
        if self.connection_state and not self.system_busy_state:
            
            # Switch to manual mode if set_man_mode is True
            if set_man_mode:
                self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_AUTO_MAN)
            else: 
                self.mmr_ctrl_reg |= (1 << MMR_CTRL_AUTO_MAN)
            
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)
            
    # Connection control
    def control_connection(self, set_connection):
        
        # Begin communicating with PLC when connection is True
        if set_connection:     
            
            # Set port and baudrate selected from connection setup
            
            self.port = self.MainWindow.port
            self.baud_rate = self.MainWindow.baud
            self.client = ModbusSerialClient(port = self.port, 
                                                stopbits = 1, 
                                                bytesize = 8, 
                                                parity = 'E', 
                                                baudrate = int(self.baud_rate),
                                                timeout = 2.0)
            self.client.connect()
            if not self.client.connected:
                QMessageBox.critical(self.MainWindow, "Error in Modbus connection", "Can't connect to Modbus")
            else:
                self.connection_state = True
                self.mmr_ctrl_reg = 0
                self.system_busy_state = False
                self.control_auto_man(True)
                self.reset_all_register()
            
            self.timer2.start(100)
            self.button_change_after_selection(self.but_ctl_con, BG_GREEN, self.but_ctl_dis, BG_WHITE)
            QMessageBox.information(self.MainWindow, "Successful connection via Modbus", "Communication begins")
            
        else:
            self.disconnetion_indicator("Disconnected")
            self.button_change_after_selection(self.but_ctl_dis, BG_RED, self.but_ctl_con, BG_WHITE)
            self.timer2.stop()
            self.client.close()
            self.system_busy_state = False
            self.control_auto_man(True)
            self.disable_manual_mode_buttons(False)
            self.connection_state = False
    
    # Start/stop control (press on SW Button)
    def control_start_stop_press(self, start, auto_mode_op = 1):
        
        # if start and not self.man_mode and self.connection_state and self.cam_open_state and not self.system_busy_state:
        if start and self.connection_state:    
            self.auto_mode_op = auto_mode_op
            self.auto_detect_indicator(ok_color = BG_WHITE, ng_color = BG_WHITE)
            self.dev_ctrl_reg |= (1 << DEV_CTRL_SW_START)
            self.run_start_time = time.perf_counter()
        
        elif not start and self.connection_state:
            self.dev_ctrl_reg |= (1 << DEV_CTRL_SW_STOP)
            
        self.client.write_register(address = DEV_CTRL_REG, value = self.dev_ctrl_reg, device_id = 1)
  
    # Start/stop control (release SW Button)
    def control_start_stop_release(self, start):
        
        if start and not self.man_mode and self.connection_state:
            self.dev_ctrl_reg &= ~(1 << DEV_CTRL_SW_START)
            
        elif not start and self.connection_state:
            self.dev_ctrl_reg &= ~(1 << DEV_CTRL_SW_STOP)
            
        self.client.write_register(address = DEV_CTRL_REG, value = self.dev_ctrl_reg, device_id = 1)  
            
#####################################################################################        
################### IMAGE SETUP PANEL (REFERENCE CAPTURE FUNCTION) ##################       
#####################################################################################     
            
    # Save reference components as a json file   
    def save_ref_data(self):
        with open("reference_component_data.json", "w") as f:
            json.dump(self.reference_comp_dict, f, indent = 4)
      
    # Load saved reference component from the file after loading screen      
    def load_ref_data(self):
        try:
            with open("reference_component_data.json", "r") as f:
                self.reference_comp_dict = json.load(f)
                self.tb_save_detection.setText(str(self.reference_comp_dict))
        except:
            pass
        
#####################################################################################        
############################### CAMERA AND DETECTION ################################       
##################################################################################### 

    # Take picture from camera after interrupt from timer 1
    def update_frame(self):
        if not self.cap.isOpened():
            self.cam_open_state = False
            QMessageBox.critical(MainWindow, "Camera is off!", "System will be off")
            return
        
        ret, self.frame = self.cap.read()
        if ret:
            self.rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            self.h, self.w, ch = self.rgb_frame.shape
            self.bytes_per_line = ch * self.w

            qt_image = QImage(self.rgb_frame.data, self.w, self.h, self.bytes_per_line, QImage.Format_RGB888)
            self.lb_cam.setPixmap(QPixmap.fromImage(qt_image))
    
    # Compare detected components with reference components, then have missing components result
    def compare_detect(self):
        no_missing_result = True
        self.missing_comp_dict = {}
        for ref_comp, ref_cnt in self.reference_comp_dict.items():
            detected_cnt = self.detected_comp_dict.get(ref_comp, 0)
            missing_cnt = ref_cnt - detected_cnt
            if missing_cnt != 0:
                self.missing_comp_dict[ref_comp] = missing_cnt
                no_missing_result = False
        return no_missing_result
         
    # Pilot indicators on supervision panel
    def auto_detect_indicator(self, ok_color, ng_color):
        self.but_sup_ng.setStyleSheet(ng_color)
        self.but_sup_ok.setStyleSheet(ok_color) 
      
    # Image capture after 1 position running is done  
    def capture_img(self):
        self.captured_images.append(cv2.rotate(self.frame, cv2.ROTATE_90_CLOCKWISE))
         
    # After taking enough images, detection is processed in new thread
    def start_detection(self):
        self.timer1.stop()
        self.worker = DetectionWorker(self.captured_images, self.imageStitcher, self.yolo_model)
        self.worker.result_ready.connect(self.handle_detection_result)
        self.worker.start()
        QMessageBox.information(self.MainWindow, "Detection in Process", "Wait for detection")

    # Detection complete, show result on screen and obtain PCB component data
    def handle_detection_result(self, data):
        
        self.timer1.start(100)
        if data["Error"] != "":
            QMessageBox.warning(self.MainWindow, "Detection Fail", data["Error"])
            return
        
        imgout = data["ImageOut"]
        obj_dict = data["ObjectDict"]             
        self.captured_images = []

        match self.auto_mode_op:
            case 1:         # Normal operation
                self.auto_detect_indicator(ok_color = BG_WHITE, ng_color = BG_WHITE)
                self.detected_comp_dict = obj_dict
                result_ok = self.compare_detect()
                if result_ok:     
                    self.mmr_ctrl_reg |= (1 << MMR_CTRL_OK)
                    self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_NG)
                    self.auto_detect_indicator(ok_color = BG_GREEN, ng_color = BG_WHITE)
                    self.table_update(ok_status = True)
                    
                    self.ok_count += 1
                    self.tb_sup_cnt_ok.setText(str(self.ok_count))

                else:
                    self.mmr_ctrl_reg |= (1 << MMR_CTRL_NG)
                    self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_OK)
                    self.auto_detect_indicator(ok_color = BG_WHITE, ng_color = BG_RED)
                    self.table_update(ok_status = False)
                    
                    self.ng_count += 1
                    self.tb_sup_cnt_ng.setText(str(self.ng_count))
                
                self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)    
                                
            case 2:         # Reference capture
                
                self.reference_comp_dict = obj_dict
                self.tb_save_detection.setText(str(self.reference_comp_dict))
        
        h, w, ch = imgout.shape
        bytes_per_line = ch * w
        qt_image = QImage(imgout, w, h, bytes_per_line, QImage.Format_RGB888)
        self.lb_detect.setPixmap(QPixmap.fromImage(qt_image))
        QMessageBox.information(self.MainWindow, "Detection Done", "Image detection complete!")

#####################################################################################        
############################### DATALOG FUNCTIONS ###################################       
##################################################################################### 

    # Table update after detection is done
    def table_update(self, ok_status):
        current_datetime = datetime.now()
        current_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        self.table_log.setRowCount(self.data_log_index + 1)
        
        self.table_log.setItem(self.data_log_index, 0, QtWidgets.QTableWidgetItem(str(self.data_log_index + 1)))
        self.table_log.setItem(self.data_log_index, 3, QtWidgets.QTableWidgetItem(current_time))
        
        if ok_status:
            self.table_log.setItem(self.data_log_index, 1, QtWidgets.QTableWidgetItem("OK"))
            self.table_log.item(self.data_log_index, 1).setBackground(QColor("lightgreen"))
        else:
            self.table_log.setItem(self.data_log_index, 1, QtWidgets.QTableWidgetItem("NG"))
            self.table_log.setItem(self.data_log_index, 2, QtWidgets.QTableWidgetItem(str(self.missing_comp_dict)))
            self.table_log.item(self.data_log_index, 1).setBackground(QColor("red"))
        
        self.data_log_index += 1
        
    # Delete table content
    def delete_table(self):
        self.table_log.clearContents()
        self.data_log_index = 0
        
    # Export to Excel
    def export_to_excel(self):
        file_name = "report_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".xlsx"
        
        # Get number of rows and columns
        row_count = self.table_log.rowCount()
        col_count = self.table_log.columnCount()

        # Get headers
        headers = [self.table_log.horizontalHeaderItem(c).text() if self.table_log.horizontalHeaderItem(c) else f"Column {c}"
                for c in range(col_count)]

        # Extract data
        data = []
        for row in range(row_count):
            row_data = []
            for col in range(col_count):
                item = self.table_log.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        # Convert to DataFrame and export to excel
        df = pd.DataFrame(data, columns=headers)
        df.to_excel(file_name, index=False)
        QMessageBox.information(self.MainWindow, "Successfully export to Excel", f"File name: {file_name} ")

#####################################################################################        
############################### SWITCH PAGES ########################################       
##################################################################################### 

    # Switch to Camera View
    def switch_to_camera_view(self):
        self.current_page = 0
        self.stwid_main.setCurrentWidget(self.page_main)
        self.stwid_panel.setCurrentWidget(self.page_panel_op)
        self.stwid_view.setCurrentWidget(self.page_cam)
    
    # Switch to System View
    def switch_to_system_view(self):
        self.current_page = 1
        self.stwid_main.setCurrentWidget(self.page_main)
        self.stwid_panel.setCurrentWidget(self.page_panel_op)
        self.stwid_view.setCurrentWidget(self.page_model)

    # Switch to Image Setup
    def switch_to_img_setup(self):
        self.current_page = 2
        self.stwid_main.setCurrentWidget(self.page_main)
        self.stwid_panel.setCurrentWidget(self.page_panel_setup)
        self.stwid_view.setCurrentWidget(self.page_cam)

    # Switch to Datalog Table
    def switch_to_datalog(self):
        self.current_page = 3
        self.stwid_main.setCurrentWidget(self.page_log)

#####################################################################################        
########################## MODBUS COMMUNICATION #####################################       
#####################################################################################

    # Read registers from PLC from timer 2 interrupt
    def receive_messenge(self):
        if not self.client.connected:
            self.control_connection(False, 0)
            return
        result = self.client.read_holding_registers(address = MMR_CTRL_REG, count = 8, device_id = 1)
            
        if result.isError():
            self.disconnetion_indicator(self.modbus_error_messenge(result.exception_code))
            pass
        else:
            self.but_stat_con.setStyleSheet(BG_DARK_GREEN)
            self.but_stat_con.setText("Connected")
            self.register_decode(result)
    
    # Modbus error indicator
    def modbus_error_messenge(self, exception_code):
        error_messenge = ["", "Illegal Function", "Illegal Data Address", "Illegal Data Value", "Slave Device Failure",
                          "Acknowledge", "Slave Device Busy", "Gateway Path Unavailable", "Gateway Target Failed to Respond"]
        return error_messenge[exception_code]
    
    # Process value from read registers
    def register_decode(self, result):
        
        # Read registers from result
        self.mmr_ctrl_reg       = result.registers[0]
        self.dev_ctrl_reg       = result.registers[1]
        self.mmr_stat_reg       = result.registers[2]
        self.dev_stat_reg       = result.registers[3]
        self.cur_pos_val        = result.registers[5] << 16 | (result.registers[4])
        self.target_pos_val     = result.registers[7] << 16 | (result.registers[6])
        
        # Signed values
        if self.cur_pos_val & 0x80000000:
            self.cur_pos_val -= 0x100000000
        if self.target_pos_val & 0x80000000:
            self.target_pos_val -= 0x100000000
            
        # Busy State
        self.system_busy_state = (self.mmr_stat_reg & (1 << MMR_STAT_BUSY)) != 0
        
        # Slide reached home (homed)
        
        if (self.dev_stat_reg & (1 << DEV_STAT_DOG)) and (self.dev_ctrl_reg & (1 << DEV_CTRL_HOMING)):
            self.dev_ctrl_reg &= ~(1 << DEV_CTRL_HOMING)
            self.client.write_register(address = DEV_STAT_REG, value = self.dev_ctrl_reg, device_id = 1)
        
        # Memory Status Position Complete Signal
        
        if (self.mmr_stat_reg & (1 << MMR_STAT_POS_CPLT)) and not self.captured_img_signal:
            
            # After a position is reached, a picture is taken
            print("POS COMPLETE ON, CAP!")
            self.capture_img()
            
            # If enough images are taken, begin detection (When Position Clear Signal is on)
            if (self.mmr_stat_reg & (1 << MMR_STAT_POS_CLEAR)) and not self.detected_img_signal:
                
                self.run_end_time = time.perf_counter()
                print(f"Running took {self.run_end_time - self.run_start_time:.4f} seconds")
                print("POS CLEAR ON, START DETECTING!")
                print("Total images: " + str(len(self.captured_images)))
                self.start_detection()
                self.detected_img_signal = True
                
            else:
                print("POS START SET!")
                self.mmr_ctrl_reg |= (1 << MMR_CTRL_POS_START)
                self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)

            self.captured_img_signal = True
            
        elif not (self.mmr_stat_reg & (1 << MMR_STAT_POS_CPLT)) and self.captured_img_signal:
            print("POS COMPLETE OFF!")
            self.captured_img_signal = False
        
        if not (self.mmr_stat_reg & (1 << MMR_STAT_POS_CLEAR)) and self.detected_img_signal:
            print("POS CLEAR OFF!")
            self.detected_img_signal = False
            
            self.end_time = time.perf_counter()
            print(f"One system cycle took {self.end_time - self.start_time:.4f} seconds")
            
        # Memory Status Position Position Processing
        
        if (self.mmr_stat_reg & (1 << MMR_STAT_POS_PROC)) and not self.pos_processing:
            
            # When position running is in process, clear position start control signal

            print("POS PROC ON, RESET POS START!")
            self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_POS_START)
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)
            self.pos_processing = True
            
        elif not (self.mmr_stat_reg & (1 << MMR_STAT_POS_PROC)) and self.pos_processing:
            print("POS PROC OFF")
            self.pos_processing = False
        
        # Memory Status Start/Stop Signal      
               
        if (self.mmr_stat_reg & (1 << MMR_STAT_START_STOP)) and not self.start_state:
            
            # Clear captures images list and begin auto mode, ready signal is on
            self.start_state = True
            self.captured_images = []
            
            self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_POS_START)
            self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_READY)
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)
            
            self.start_time = time.perf_counter()
        elif not (self.mmr_stat_reg & (1 << MMR_STAT_START_STOP)) and self.start_state:
            
            # Clear start button control when released (toggle button), ready signal is off
            self.start_state = False
            
            self.mmr_ctrl_reg |= (1 << MMR_CTRL_READY)  
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)
            
        # Memory Status Auto/Man Signal
        
        if (self.mmr_stat_reg & (1 << MMR_STAT_AUTO_MAN)) and self.man_mode:
            
            # Change to Auto Mode
            self.man_mode = False
            self.disable_manual_mode_buttons(True)
            self.mmr_ctrl_reg |= (1 << MMR_CTRL_READY)
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)

        elif not (self.mmr_stat_reg & (1 << MMR_STAT_AUTO_MAN)) and not self.man_mode:
            
            # Change to Manual Mode
            self.man_mode = True
            self.disable_manual_mode_buttons(False)
            self.mmr_ctrl_reg &= ~(1 << MMR_CTRL_READY)
            self.client.write_register(address = MMR_CTRL_REG, value = self.mmr_ctrl_reg, device_id = 1)

        
        
        # Monitor Devices
        
        if (self.current_page == 0 or self.current_page == 1):
            self.change_button_color(self.but_ctl_start,        BG_GREEN, self.mmr_stat_reg,  MMR_STAT_START_STOP)
            self.change_button_color(self.but_ctl_stop,         BG_RED,   ~self.mmr_stat_reg, MMR_STAT_START_STOP)
            self.change_button_color(self.but_ctl_mode_auto,    BG_BLUE,  self.mmr_stat_reg,  MMR_STAT_AUTO_MAN)
            self.change_button_color(self.but_ctl_mode_man,     BG_BLUE,  ~self.mmr_stat_reg, MMR_STAT_AUTO_MAN)
            self.change_button_color(self.but_sup_ready,        BG_BLUE,  self.mmr_stat_reg,  MMR_STAT_READY)
            self.tb_man_ctrl_cur_pos.setText(str(self.cur_pos_val))
            
        if (self.current_page == 1): 
            self.change_button_color(self.but_view_light,   BG_GREEN, self.dev_stat_reg, DEV_STAT_LIGHT)
            self.change_button_color(self.but_view_jog_for, BG_GREEN, self.dev_stat_reg, DEV_STAT_JOG_FOR)
            self.change_button_color(self.but_view_jog_rev, BG_GREEN, self.dev_stat_reg, DEV_STAT_JOG_REV)
            self.change_button_color(self.but_view_home,    BG_GREEN, self.dev_stat_reg, DEV_STAT_HOMING)
            self.change_button_color(self.but_view_dog,     BG_GREEN, self.dev_stat_reg, DEV_STAT_DOG)
            
            self.change_button_color(self.but_view_ls_for,  BG_GREEN, self.dev_stat_reg, DEV_STAT_LS_FOR)
            self.change_button_color(self.but_view_ls_rev,  BG_GREEN, self.dev_stat_reg, DEV_STAT_LS_REV)
            self.change_button_color(self.but_view_ss_pcb,  BG_GREEN, self.dev_stat_reg, DEV_STAT_SS_PCB)
            self.change_button_color(self.but_view_for,     BG_GREEN, self.dev_stat_reg, DEV_STAT_FOR)
            self.change_button_color(self.but_view_rev,     BG_GREEN, self.dev_stat_reg, DEV_STAT_REV)
            
            self.tb_view_current.setText(str(self.cur_pos_val))
            self.tb_view_target.setText(str(self.target_pos_val))
            
        # l = [] 
        # for val in result.registers:
        #     l.append(hex(val))
        # print(l)
            
    # Change color of indicator depending on received registers for supervision
    def change_button_color(self, button, color, reg, reg_index):
        button.setStyleSheet(color) if (reg & (1 << reg_index)) else button.setStyleSheet(BG_WHITE)
        
#####################################################################################        
########################## POSITION TABLE FUNCTIONS #################################       
#####################################################################################

    # Load position data onto table
    def load_pos_table(self):
        
        # When loading table, open the file that has saved the previous positions if the file exist,
        # Otherwise create a table with all value 0
        try:
            with open("table_data2.json", "r") as f:
                data = json.load(f)

            self.table_pos.setRowCount(len(data[0]))

            for row, row_data in enumerate(data[0]):
                for col, value in enumerate(row_data):
                    self.table_pos.setItem(row, col, QTableWidgetItem(value))
                    
            self.tb_view_vel.setText(data[1][0])
            self.tb_view_pos_num.setText(data[2][0])

        except:
            row_count = self.table_pos.rowCount()
            for row in range(row_count):
                self.table_pos.setItem(row, 1, QTableWidgetItem("0"))

    # Save position data from table into a json file
    def save_pos_table(self):
        rows = self.table_pos.rowCount()
        cols = self.table_pos.columnCount()

        data = []
        pos_data = []
        vel_data = [self.tb_view_vel.toPlainText()]
        pos_num  = [self.tb_view_pos_num.toPlainText()]

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table_pos.item(row, col)
                if item:
                    row_data.append(item.text())
                else:
                    row_data.append("")
            pos_data.append(row_data)
            
        data.append(pos_data)
        data.append(vel_data)
        data.append(pos_num)

        with open("table_data2.json", "w") as f:
            json.dump(data, f, indent = 4)
      
    # Send position data to PLC via Modbus
    def send_motor_param_data(self):
        if self.connection_state:
            
            # Send positioning data
            
            rows = self.table_pos.rowCount()
            for row in range(rows):
                
                # Validate data before sending in case of invalid datatype or out of range value
                try:
                    pos_value = int(self.table_pos.item(row, 0).text())
                except:
                    QMessageBox.critical(self.MainWindow, "Invalid Position Data", "Exist inproper data in table")
                    return
                if 0 <= pos_value <= MAX_POS_VALUE:
                    self.pos_data_regs[row * 2] = pos_value & 0xFFFF
                    self.pos_data_regs[row * 2 + 1] = (pos_value >> 16) & 0xFFFF
                else:
                    QMessageBox.critical(self.MainWindow, "Invalid Position Data", f"Data should be in range of 0 and {MAX_POS_VALUE}")
                    return
            
            # Send velocity data
            
            try:
                vel_value = int(self.tb_view_vel.toPlainText())
            except:
                QMessageBox.critical(self.MainWindow, "Invalid Setting Velocity", "Inproper setting velocity data")
                return
            
            if 0 <= vel_value <= MAX_VEL_VALUE:
                vel_values = [0] * 6
                for i in range(3):
                    vel_values[i * 2] = vel_value & 0xFFFF
                    vel_values[i * 2 + 1] = (vel_value >> 16) & 0xFFFF   
            else:
                QMessageBox.critical(self.MainWindow, "Invalid Velocity Data", f"Data should be in range of 0 and {MAX_VEL_VALUE}")
                return
            
            try:
                pos_num = int(self.tb_view_pos_num.toPlainText())
            except:
                QMessageBox.critical(self.MainWindow, "Invalie Number of Positioning", "Inproper setting data")
                return
            
            # Send number of positioning data
            
            if 0 <= pos_num <= MAX_POS_NUM:
                pos_num = pos_num * 2 - 2
            else:
                QMessageBox.critical(self.MainWindow, "Invalid Positioning Number", f"Data should be in range of 0 and {MAX_POS_NUM}")
                return
            
            # Sending Process
            
            self.client.write_registers(address = POS1_DATA_REG, values = self.pos_data_regs, device_id = 1)
            self.client.write_registers(address = SET_VEL_REG, values = vel_values, device_id = 1)
            self.client.write_register(address = POS_NUM_REG, value = pos_num, device_id = 1)
    
#####################################################################################        
############################### OTHER FUNCTIONS #####################################       
##################################################################################### 
    
    # When switch to auto mode, all manual mode related button is disabled
    def disable_manual_mode_buttons(self, set_auto_mode):
        if set_auto_mode:
            self.but_view_home.setDisabled(True)
            self.but_view_jog_for.setDisabled(True)
            self.but_view_jog_rev.setDisabled(True)
            self.but_view_light.setDisabled(True)
            self.but_view_pos_send.setDisabled(True)
            
            self.but_man_ctrl_home.setDisabled(True)
            self.but_man_ctrl_jog_for.setDisabled(True)
            self.but_man_ctrl_jog_rev.setDisabled(True)
            
            self.but_img_ref.setEnabled(True)
            self.but_img_stop.setEnabled(True)
        else:
            self.but_view_home.setEnabled(True)
            self.but_view_jog_for.setEnabled(True)
            self.but_view_jog_rev.setEnabled(True)
            self.but_view_light.setEnabled(True)
            self.but_view_pos_send.setEnabled(True)
            
            self.but_man_ctrl_home.setEnabled(True)
            self.but_man_ctrl_jog_for.setEnabled(True)
            self.but_man_ctrl_jog_rev.setEnabled(True)
            
            self.but_img_ref.setDisabled(True)
            self.but_img_stop.setDisabled(True)
            
    # When choosing one option of button in control panel then state of button will be changed
    def button_change_after_selection(self, disable_but, color1, enable_but, color2):
        # disable_but.setDisabled(True)
        disable_but.setStyleSheet(color1)
        
        # enable_but.setEnabled(True)
        enable_but.setStyleSheet(color2)
        
    # Side panel button color change
    def side_button_change_after_selection(self, selected_page_button):
        self.but_side_cam.setStyleSheet("background-color: hsl(0,0,50)")
        self.but_side_view.setStyleSheet("background-color: hsl(0,0,50)")
        self.but_side_setup.setStyleSheet("background-color: hsl(0,0,50)")
        self.but_side_log.setStyleSheet("background-color: hsl(0,0,50)")
        
        selected_page_button.setStyleSheet("background-color: hsl(0,0,150)")
        
    # Send device manual control signal to PLC  
    def manual_control(self, control_command):
        
        if self.connection_state and self.man_mode:
            match control_command:
                case "LIGHT": 
                    if self.dev_stat_reg & (1 << DEV_STAT_LIGHT):
                        self.dev_ctrl_reg &=~ (1 << DEV_CTRL_LIGHT)
                    else:
                        self.dev_ctrl_reg |= (1 << DEV_CTRL_LIGHT)
                case "JOG+ ON": 
                    self.dev_ctrl_reg     |= (1 << DEV_CTRL_JOG_FOR)
                case "JOG+ OFF": 
                    self.dev_ctrl_reg &=~ (1 << DEV_CTRL_JOG_FOR)
                case "JOG- ON": 
                    self.dev_ctrl_reg |= (1 << DEV_CTRL_JOG_REV)
                case "JOG- OFF": 
                    self.dev_ctrl_reg &=~ (1 << DEV_CTRL_JOG_REV)
                case "HOME": 
                    if self.dev_stat_reg & (1 << DEV_STAT_HOMING):
                        self.dev_ctrl_reg &=~ (1 << DEV_CTRL_HOMING)
                    else:
                        self.dev_ctrl_reg |= (1 << DEV_CTRL_HOMING)
        
            try:
                self.client.write_register(address = DEV_CTRL_REG, value = self.dev_ctrl_reg, device_id = 1)
            except:
                pass   

    # Show connection dialog when choosing connection setup
    def show_connection_dialog(self):
        ConnectionDialog = QDialog()
        ConnectionWindow_ui = Ui_ConnectionDialog_Class()
        ConnectionWindow_ui.setupUi(ConnectionDialog)
        ConnectionWindow_ui.modifyUi(ConnectionDialog, self.MainWindow)
        ConnectionDialog.show()

    # Disconnection state indicator
    def disconnetion_indicator(self, connection_text):
        self.but_stat_con.setStyleSheet(BG_DARK_RED)
        self.but_stat_con.setText(connection_text)
       
    # Reset OK and NG count on supervision panel       
    def reset_count(self):
         self.tb_sup_cnt_ok.setText("0")
         self.tb_sup_cnt_ng.setText("0")
         self.ok_count = 0
         self.ng_count = 0

    # Reset all state of registers on PLC
    def reset_all_register(self):
        self.mmr_ctrl_reg = 0
        self.dev_ctrl_reg = 0
        self.mmr_stat_reg = 0
        self.dev_stat_reg = 0
        self.cur_pos_val = 0
        self.target_pos_val = 0
        zero = [0] * 8
        self.client.write_registers(address = MMR_CTRL_REG, values = zero, device_id = 1)
              
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    ui = Ui_MainWindow_Class(mainwindow)
    sys.exit(app.exec_())

        
    

    
    
        

