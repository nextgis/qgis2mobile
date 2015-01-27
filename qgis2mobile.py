# -*- coding: utf-8 -*-

#******************************************************************************
#
# qgis2mobile
# ---------------------------------------------------------
#
# Copyright (C) 2012-2013 NextGIS (info@nextgis.org)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/licenses/>. You can also obtain it by writing
# to the Free Software Foundation, 51 Franklin Street, Suite 500 Boston,
# MA 02110-1335 USA.
#
#******************************************************************************
import os, sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from qgis.core import *
from qgis.gui import QgsMessageBar


def getRemovableDevices():
    removableDevices = []
    
    if sys.platform == "win32":
        from win32api import GetLogicalDriveStrings, GetVolumeInformation
        from win32file import GetDriveType
        
        drives = GetLogicalDriveStrings()
        drives = drives.split('\000')[:-1]
        for drive in drives:
            if GetDriveType(drive) == 2:
                try:
                    removableDevices.append(list(GetVolumeInformation(drive)) + [drive])
                except:
                    QgsMessageLog.logMessage( "GetVolumeInformation error ", u'qgis2mobile', QgsMessageLog.CRITICAL)
    else:
        pass
        
    return removableDevices
        

SETTINGS_DIALOG, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis2mobile_settings.ui'))

class SettingsDialog(QDialog, SETTINGS_DIALOG):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        
        settings = QSettings();
        self.usbDeviceID = settings.value("qgis2mobile/device_id", -1,  type=int)
        self.importDirectory = settings.value("qgis2mobile/import_dir", "", type=unicode)
        self.lePathToImport.setText(self.importDirectory)
        
        self.pbBrowse.clicked.connect(self.browseProcess)
        self.cbDevices.activated.connect(self.selectOtherDeviceProc)
        
        self.fillingDevices()
        self.checkPBBrowseStatus()
        
    def accept(self):
        settings = QSettings();
        
        settings.setValue("qgis2mobile/device_id", self.usbDeviceID)
        
        self.importDirectory = self.lePathToImport.text()
        settings.setValue("qgis2mobile/import_dir", self.importDirectory)
        
        super(SettingsDialog, self).accept()
    
    def checkPBBrowseStatus(self):
        drives = getRemovableDevices()
        for drive in drives:
            if drive[1] == self.usbDeviceID:
                self.pbBrowse.setEnabled(True)
                return
        self.pbBrowse.setEnabled(False)
    
    def browseProcess(self):
        drives = getRemovableDevices()
        for drive in drives:
            if drive[1] == self.usbDeviceID:
                default_path = os.path.join(drive[5], self.lePathToImport.text())
                if not os.path.exists(default_path):
                    default_path = drive[5]
                    
                dirName = QFileDialog.getExistingDirectory(self,
                                       self.tr("Select directory"),
                                       default_path,
                                       QFileDialog.ShowDirsOnly
                                      )
                dirName = unicode(dirName)
                if dirName != "" and dirName.find(drive[5]) == 0:
                    self.importDirectory = dirName.replace(drive[5], '')
                    self.lePathToImport.setText(self.importDirectory)

    def selectOtherDeviceProc(self, index):
        self.usbDeviceID = self.cbDevices.itemData(index)
        self.checkPBBrowseStatus()
    
    def devicesChanged(self):
        self.fillingDevices()
        self.checkPBBrowseStatus()
        
    def fillingDevices(self):
        self.cbDevices.clear()
        drive_with_id_found = False
        
        drives = getRemovableDevices()
        for drive in drives:
            volume_name = drive[0]
            if volume_name == '':
                volume_name = self.tr("Removable disk")
            volume_description = "%s(%s) id: %d"%(volume_name, drive[5], drive[1])
            cb_insert_index = 1
            if drive[1] == self.usbDeviceID:
                drive_with_id_found = True
                volume_description = volume_description + " (%s)"%self.tr("curent")
                cb_insert_index = 0
            
            self.cbDevices.insertItem(cb_insert_index, volume_description, drive[1])
        
        if not drive_with_id_found:
            self.cbDevices.insertItem(0, "Current volume serial number is %d (not found now)"%self.usbDeviceID, self.usbDeviceID)
        self.cbDevices.setCurrentIndex(0)
        
class DeviceListener(QThread):
    deviceConnected = pyqtSignal()
    deviceDisconnected = pyqtSignal()
    devicesChanged = pyqtSignal()
    def __init__(self):
        QThread.__init__(self)
        self.deviceAlreadyConnected = False
        self.setting = QSettings()
        self.lastCheckDevices = []
    def __del__(self):
        self.wait()
        
    def run(self):
        while(True):
            self.usleep(1000000)
            self.findRemovableDrives()
            
    def findRemovableDrives(self):
        usbDeviceID = self.setting.value("qgis2mobile/device_id", -1,  type=int)
        
        specified_driver_found = False
        foundDevicesIds = []
        
        drives = getRemovableDevices()
        for drive in drives:
            #QgsMessageLog.logMessage( "drive: " + str(drive), u'qgis2mobile', QgsMessageLog.INFO)
            foundDevicesIds.append(drive[1])
            if drive[1] == usbDeviceID:
                specified_driver_found = True
                if self.deviceAlreadyConnected == False:
                    QgsMessageLog.logMessage( "Device connected", u'qgis2mobile', QgsMessageLog.INFO)
                    self.deviceAlreadyConnected = True
                    self.deviceConnected.emit()
        
        if specified_driver_found == False and self.deviceAlreadyConnected == True:
            QgsMessageLog.logMessage( "Device disconnected", u'qgis2mobile', QgsMessageLog.INFO)
            self.deviceAlreadyConnected = False
            self.deviceDisconnected.emit()
        
        self.lastCheckDevices.sort()
        foundDevicesIds.sort()
        if self.lastCheckDevices != foundDevicesIds:
            self.lastCheckDevices = foundDevicesIds
            self.devicesChanged.emit()
class MyAction(QAction):
    def __init__(self, parent):
        QAction.__init__(self, parent)

        
class Plugin():
  def __init__(self, iface):

    self.iface = iface

    self.qgsVersion = unicode(QGis.QGIS_VERSION_INT)

    # For i18n support
    self.userPluginPath = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/qgis2mobile"
    systemPluginPath = QgsApplication.prefixPath() + "/python/plugins/qgis2mobile"

    overrideLocale = bool(QSettings().value("locale/overrideFlag", False, bool))
    if not overrideLocale:
      localeFullName = QLocale.system().name()[:2]
    else:
      localeFullName = QSettings().value("locale/userLocale", "")

    if QFileInfo(self.userPluginPath).exists():
      translationPath = self.userPluginPath + "/i18n/qgis2mobile_" + localeFullName + ".qm"
    else:
      translationPath = systemPluginPath + "/i18n/qgis2mobile_" + localeFullName + ".qm"
    
    self.localePath = translationPath
    if QFileInfo(self.localePath).exists():
      self.translator = QTranslator()
      self.translator.load(self.localePath)
      QCoreApplication.installTranslator(self.translator)
    
  def initGui(self):
    self.actionRun = QAction(self.iface.mainWindow())
    self.actionRun.setIcon(QIcon(self.userPluginPath + "/icons/qgis2mobile.png"))
    self.actionRun.setWhatsThis("Import layer to USB device")
    self.actionRun.setCheckable(False)
    
    self.actionRun.setText(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setStatusTip(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setToolTip(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setEnabled(False)
    self.actionRun.triggered.connect(self.startImport)
    
    self.actionSettings = QAction(QCoreApplication.translate("Plugin", "Settings"), self.iface.mainWindow())
    self.actionSettings.setIcon(QIcon(self.userPluginPath + "/icons/qgis2mobile.png"))
    self.actionSettings.triggered.connect(self.showSettings)
    
    self.iface.fileToolBar().addAction(self.actionRun)
    self.iface.addPluginToMenu(QCoreApplication.translate("Plugin", "qgis2mobile"), self.actionRun)
    self.iface.addPluginToMenu(QCoreApplication.translate("Plugin", "qgis2mobile"), self.actionSettings)
    
    self.thread = DeviceListener()
    self.thread.deviceConnected.connect(self.deviceConnectProcess)
    self.thread.deviceDisconnected.connect(self.deviceDisconnectProcess)
    self.thread.started.connect(self.treadStartProcess)
    
    if sys.platform == "win32":
        self.thread.start()
    else:
        self.actionRun.setEnabled(False)
        self.actionRun.setText(QCoreApplication.translate("Plugin", "Linux not support"))
        self.actionRun.setStatusTip(QCoreApplication.translate("Plugin", "Linux not support"))
        self.actionRun.setToolTip(QCoreApplication.translate("Plugin", "Linux not support"))
    
        self.actionSettings.setEnabled(False)
  
  def treadStartProcess(self):
    QgsMessageLog.logMessage( "USB device listener START", u'qgis2mobile', QgsMessageLog.INFO)
  
  def deviceConnectProcess(self):
    self.actionRun.setEnabled(True)
    self.actionRun.setText(QCoreApplication.translate("Plugin", "Import layer to device"))
    self.actionRun.setStatusTip(QCoreApplication.translate("Plugin", "Import layer to device"))
    self.actionRun.setToolTip(QCoreApplication.translate("Plugin", "Import layer to device"))
    
    self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                        QCoreApplication.translate("Plugin", 'The device is connected'),
                                                level=QgsMessageBar.INFO)
  def deviceDisconnectProcess(self):
    self.actionRun.setText(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setStatusTip(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setToolTip(QCoreApplication.translate("Plugin", "No device to import"))
    self.actionRun.setEnabled(False)
    
    self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                        QCoreApplication.translate("Plugin", 'The device is disconnected'),
                                        level=QgsMessageBar.WARNING)

    
  def unload(self):
    self.thread.exit()
    self.iface.fileToolBar().removeAction(self.actionRun)
    self.iface.removePluginMenu(QCoreApplication.translate("Plugin", "qgis2mobile"), self.actionRun)
    self.iface.removePluginMenu(QCoreApplication.translate("Plugin", "qgis2mobile"), self.actionSettings)

  def showSettings(self):
    settingsDialog = SettingsDialog()
    self.thread.devicesChanged.connect(settingsDialog.devicesChanged)
    settingsDialog.exec_()
    
  def startImport(self):
    settings = QSettings()
    usbDeviceID = settings.value("qgis2mobile/device_id", -1,  type=int)
    importDirectory = settings.value("qgis2mobile/import_dir", "", type=unicode)
    
    possibleSpatialRefs = [u'EPSG:4326', u'EPSG:3857']
    
    QgsMessageLog.logMessage( "Import START ", u'qgis2mobile', QgsMessageLog.INFO)
    
    if usbDeviceID == -1:
        QgsMessageLog.logMessage( "Import ERROR: Plugin is not configured", u'qgis2mobile', QgsMessageLog.CRITICAL)
        self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                            QCoreApplication.translate("Plugin", 'Plugin is not configured'),
                                            level=QgsMessageBar.CRITICAL)
    
    currentLayer = self.iface.mapCanvas().currentLayer()
    if currentLayer is None:
        QgsMessageLog.logMessage( "Import ERROR: layer is not selected", u'qgis2mobile', QgsMessageLog.CRITICAL)
        self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                            QCoreApplication.translate("Plugin", 'Layer is not selected'),
                                            level=QgsMessageBar.CRITICAL)
        return
    if currentLayer.type() != QgsMapLayer.VectorLayer:
        QgsMessageLog.logMessage( "Import ERROR: selected layer is not a vector", u'qgis2mobile', QgsMessageLog.CRITICAL)
        self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                            QCoreApplication.translate("Plugin", 'Selected layer is not a vector'),
                                            level=QgsMessageBar.CRITICAL)
        return
    QgsMessageLog.logMessage( "\t Layer: %s"%currentLayer.name(), u'qgis2mobile', QgsMessageLog.INFO)
    
    QgsMessageLog.logMessage( "\t crs: %s"%currentLayer.crs().authid(), u'qgis2mobile', QgsMessageLog.INFO)
    if currentLayer.crs().authid() not in possibleSpatialRefs:
        QgsMessageLog.logMessage( "Import ERROR: Layer spatial reference have to be one of %s"%str(possibleSpatialRefs), u'qgis2mobile', QgsMessageLog.CRITICAL)
        self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                            QCoreApplication.translate("Plugin", 'Layer spatial reference have to be one of %s'%str(possibleSpatialRefs)),
                                            level=QgsMessageBar.CRITICAL)
        return
    
    drives = getRemovableDevices()
    for drive in drives:
        if drive[1] == usbDeviceID:
            if not os.path.exists(os.path.join(drive[5], importDirectory)):
                QgsMessageLog.logMessage( "Import ERROR: directory %s for import not found"%os.path.join(drive[5], importDirectory), u'qgis2mobile', QgsMessageLog.CRITICAL)
                self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                                    QCoreApplication.translate("Plugin", "Directory %s for import not found"%os.path.join(drive[5], importDirectory)),
                                                    level=QgsMessageBar.CRITICAL)
                return
            
            import_filename = os.path.join(drive[5], importDirectory, "%s.json"%currentLayer.name())
            QgsMessageLog.logMessage( "\t save as: %s"%import_filename, u'qgis2mobile', QgsMessageLog.INFO)
            
            error = QgsVectorFileWriter.writeAsVectorFormat(currentLayer, import_filename, "utf-8", None, "GeoJSON")
            if error != QgsVectorFileWriter.NoError:
                QgsMessageLog.logMessage( "Import ERROR: QgsVectorFileWriter ERROR", u'qgis2mobile', QgsMessageLog.CRITICAL)
                self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                                    QCoreApplication.translate("Plugin", 'Import ERROR: QgsVectorFileWriter ERROR'),
                                                    level=QgsMessageBar.CRITICAL)
            else:
                QgsMessageLog.logMessage( "Import FINISH ", u'qgis2mobile', QgsMessageLog.INFO)
                self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                                    QCoreApplication.translate("Plugin", 'The import was successful!'),
                                                    level=QgsMessageBar.INFO)
                                                    
            return

    QgsMessageLog.logMessage( "Import ERROR:  usb volume not found", u'qgis2mobile', QgsMessageLog.CRITICAL)
    self.iface.messageBar().pushMessage(QCoreApplication.translate("Plugin", 'qgis2mobile'),
                                        QCoreApplication.translate("Plugin", 'Usb device with id %d not found'%usbDeviceID),
                                        level=QgsMessageBar.CRITICAL)
    
