# PyQt5 Libraries
from PyQt5.QtWidgets import (
    QDialog, QMessageBox, QApplication
)

# Built-in Libraries
from serial.tools.list_ports import comports


# My Libraries
from ui_connection_dialog import Ui_Connection_Dialog
        
class Ui_ConnectionDialog_Class(Ui_Connection_Dialog):

    # Added function calls to Ui
    def modifyUi (self, ConnectionDialog, MainWindow):
        
        # Button functions
        self.but_con_setup_ok.clicked.connect(lambda: self.connection_save(ConnectionDialog, MainWindow))
        self.but_con_setup_cancel.clicked.connect(lambda: self.connection_cancel(ConnectionDialog))
        self.but_con_setup_refresh.clicked.connect(lambda: self.connection_port_refresh())
        
        # Load ComboBox selections
        self.connection_port_refresh()
        self.cb_con_setup_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.cb_con_setup_baud.setCurrentIndex(self.cb_con_setup_baud.findText("9600")) # Default baud rate value
        
        
    # Cancel button function
    def connection_cancel(self, ConnectionDialog):
        ConnectionDialog.close()
        
    # Refresh button function to reload ports
    def connection_port_refresh(self):
        ports = comports()
        self.cb_con_setup_port.clear()
        for port in ports:
            self.cb_con_setup_port.addItem(str(port).split()[0])
        port_def = self.cb_con_setup_port.findText("COM3")
        if port_def >= 0:
            self.cb_con_setup_port.setCurrentIndex(port_def)
    
    # Save button to save communication definition
    def connection_save(self, ConnectionDialog, MainWindow):
        
        # Save selected port and baud
        selected_port = self.cb_con_setup_port.currentText()
        selected_baud = self.cb_con_setup_baud.currentText()

        # Warning dialog shows when port or baud is not selected
        if not selected_port or not selected_baud:
            QMessageBox.warning(ConnectionDialog, "Warning", "Please select COM port and baudrate properly!")
            return
        
        # Successfully selected
        MainWindow.pass_connection_param(selected_port, selected_baud)            
        QMessageBox.information(ConnectionDialog, "Success", f"COM Port: {selected_port}\nBaudrate: {selected_baud}")
        ConnectionDialog.close()
        
