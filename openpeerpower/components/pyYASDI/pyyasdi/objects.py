about = """
Title: pyYASDI
Autor: Sebastian Schulte
Version: 1.0.0
Date: 18.3.07 / 18.3.07 / 18.3.07
File: pyYASDI.py

+ SMA YASDI Library Wrapper for Python 3"""

import logging

import pyyasdi.yasdiwrapper as yasdiwrapper


logger = logging.getLogger(__name__)


class Plant:
    """pyYASDI - supports SMANet service"""
    def __init__(self,driver=0,debug=1,max_devices=1):
        """Constructor
                Parameter:
                driver = 0          0 = 1.Driver in yasdi.ini
                debug = 1/0         1 = on or 0 = off
                max_devices = 1     maximum devices to search for"""
        self.max_devices = max_devices
        self.debug = debug
        self.driver = driver
        self.DeviceList = []
        self.YasdiMaster = yasdiwrapper.YasdiMaster()
        self.Yasdi = yasdiwrapper.Yasdi()
        self.YasdiMaster.yasdiMasterInitialize()

        self.DriverName = self.goOnline(self.driver)
        if self.DriverName == 0: self.The()
        result =  self .detectDevices ( self .max_devices)
        self.load_devices()

    def msg(self,msg,error=0):
        """msg Method for Debugging output
                Parameter:
                msg =               The message output / shall be saved
                error = 0           error = 0 Status error = 1 error message"""
        if error == 0:
            if self.debug: print(":>        %s"%(msg))
        elif error == 1:
            if self.debug: print(":> Error: %s"%(msg))

    def quit(self):
        """Completed the Yasdi-Master and free up resources"""
        self.YasdiMaster.yasdiMasterShutdown()

    def The(self):
        """Completed the Yasdi-Master by virtue of a failure"""
        self.msg("Died",1)
        self.quit()

    def goOnline(self,driver):
        """Switch on the interface 
                Parameter:
                driver              0 = 1. Interface in yasdi.ini usw.
                Result:
                0 in error or e.g.
                COM1 When the first serial port was loaded"""
        anzdriver = self.Yasdi.yasdiGetDriver()
        if anzdriver == 0:
            self.msg("Could not load interface",1)
            return anzdriver
        else:
            self.Yasdi.yasdiSetDriverOnline(driver)
            DriverName = self.Yasdi.yasdiGetDriverName(driver)
            self.msg("Interface %s ready"%(DriverName))
            return DriverName

    def detectDevices(self,max_devices):
        """Devices detection
                Parameter:
                max_devices max. Devices to search for
                Result:
                0 when not all devices are found
                1 when all devices are found"""
        result = self.YasdiMaster.DoMasterCmdEx(max_devices)
        if result == -1:
            self.msg("Can not find all %s devices"%(self.max_devices),1)
            return 0
        elif not result:
            self.msg("Can find all devices",0)
            return 1

    def get_masterstatus(self):
        """Gives the Status the Masters back, per return and print
                Results:
                1 = Initial State of the Machine
                2 = Devices acquisition
                3 = set the Network addresses
                4 = Query the channel lists
                5 = Master-Command processing
                6 = Channels read (Spot or Parameter)
                7 = Channels write (only Parameter)"""
        result = self.YasdiMaster.GetMasterStateIndex()
        self.msg("Yasdi-Master Status: %s"%(result),0)
        return result

    def reset(self):
        """Puts the Yasdi-Master back in the Initialisation state"""
        self.quit()
        self.__init__(self.driver,self.debug,self.max_devices)

    def load_devices(self):
        """Load the device found by Device Sub Class"""
        self.devicehandleslist = self.YasdiMaster.GetDeviceHandles()
        for i in self.devicehandleslist:
            if i != 0:
                self.DeviceList.append(Device(handle=i,master=self.YasdiMaster,debug=self.debug))

    def get_devices(self):
        """Gives the loaded devices back
                Results:
                Device-Class one each Unit"""
        return self.DeviceList

    def data_device (self, device, parameter_channel=True):
        logger.info ("read device {}". format (device.get_name ()))
        data = {}
        for n, i in enumerate (device.channels):
            if not parameter_channel and i.parameter_channel:
                # ignore parameter channel
                logger.info ("\ tignore parameter channel")
                continue

            i.update_name ()
            logger.info ("\ tread channel {}". format (i.get_name ()))

            i.update_value ()
            value, text, timestamp = i.value

            # set value to interesting information
            # if text then text, otherwise the value
            value_interesting = text
            if not value_interesting:
                value_interesting = value

            data [i.get_name ()] = value

        return data

    def data_all(self, parameter_channel=True):
        """get data of all devices and channels

        Args:
            parameter_channel (bool): If true, from spot and prameter channel.
            Otherwise only from spot channels.

        Returns:
            data (dict): of all channels of all devices
        """
        data_all = {}
        for d in self.get_devices():
            data_all['{}-{}'.format(d.get_type(), d.get_sn())] = self.data_device(d, parameter_channel)

        print(data_all)

        return data_all

class Device:
    """Device Class with the potential characteristics and methods of one devices (Inverter and SunnyBC etc.)"""
    def __init__(self,handle,master,debug=0):
        """Constructor
                Parameter:
                handle = devices handle
                master = Master Class
                debug = 0           If 1 returns debug messages"""
        self.handle = handle
        self.master = master
        self.debug = debug
        self.channels = []

        result = self.update_all(nochannels=0)

        self.name = result[0]
        self.sn = result[1]
        self.type = result[2]

    def msg(self,msg,error=0):
        """msg Method for Debug Output etc.
                Parameter:
                msg =               The Message The output / saved worth it
                error = 0           error = 0 Status error = 1 Error Messages"""
        if error == 0:
            if self.debug: print(":>        %s"%(msg))
        elif error == 1:
            if self.debug: print(":> Error: %s"%(msg))

    def update_name(self):
        """Updated the Device name and Give back"""
        result = self.master.GetDeviceName(self.handle)
        self.msg("Deviceename %s"%(result),0)
        return result
        
    def update_sn(self):
        """Updated The Device SN and Give back"""
        result = self.master.GetDeviceSN(self.handle)
        self.msg("DeviceeSN %s"%(result),0)
        return result

    def update_type(self):
        """Updated the Deviceetypen and Give it back"""
        result = self.master.GetDeviceType(self.handle)
        self.msg("Deviceetyp %s"%(result),0)
        return result

    def update_channels(self):
        """Updated The Channel des Devicees and Give The Channel Handles back"""
        result = self.master.GetChannelHandles(handle=self.handle,parameter_channel=0)
        self.channels = []
        for i in result:
            if i != 0:
                self.channels.append(Channel(channel_handle=i,device_handle=self.handle,parameter_channel=0,master=self.master))
                self.msg("Deviceespotchannel      %s"%(i),0)

        result = self.master.GetChannelHandles(handle=self.handle,parameter_channel=1)
        for i in result:
            if i != 0:
                self.channels.append(Channel(channel_handle=i,device_handle=self.handle,parameter_channel=1,master=self.master))
                self.msg("Deviceeparameterchannel %s"%(i),0)

        return self.channels

    def update_all(self,noname=0,nosn=0,notype=0,nochannels=0):
        """Updated all, the complete Device
                Parameter:
                noname = 0          set to true to not refresh the name
                nosn = 0            if true, do not refresh SN
                notype = 0          if true, do not refresh type
                nochannels = 0      if true, do not refresh channels
                Ergebnis:
                Tupel (name,sn,type,channels)"""
        name = 0
        sn = 0
        typ = 0
        channels = 0

        if not noname: name = self.update_name()
        if not nosn: sn = self.update_sn()
        if not notype: typ = self.update_type()                 # type nicht erlaubt weil wegen Schluesselwort
        if not nochannels: channels = self.update_channels()

        return (name,sn,typ,channels)

    def get_name(self):
        """Give the Device Name back"""
        return self.name

    def get_sn(self):
        """Give The Device SN back"""
        return self.sn

    def get_type(self):
        """Give the Device Type back"""
        return self.type

    def get_channels(self):
        """Give The Device Channel back"""
        return self.channels

    def get_formatted(self):
        """Formatted Output the Devices, The Channel werthe ink. Value individually Updated"""
        print("Formatted report for Device %s:"%(self.get_name()))
        for i in self.channels:
            name = i.update_name()
            value = i.update_value()
            unit = i.update_unit()
            if value == -3: self.msg("Channeltimeout for %s"%(i),1)
            else: print("%s  = %s%s"%(name,value[0],unit))

class Channel:
    """Constructor
            Parameter:
            channel_handle          HandleNummer Theses Channel s
            device_handle           DeviceeNummer Theses Channel s
            parameter_channel       0 = Spot Channel 1 = Parameter Channel
            max_channel_age = 60    max. Older one Spot Channels"""
    def __init__(self,channel_handle,device_handle,parameter_channel,master,max_channel_age=60):
        self.channel_handle = channel_handle
        self.device_handle = device_handle
        self.max_channel_age = max_channel_age
        self.parameter_channel = parameter_channel
        self.master = master
        self.name = ""
        self.statustext = []            #Either List with Status texts or when it no for This Channel Give  | -1 when Channel handle invalid
        self.unit = ""
        self.range = 0
        self.value = [0,"",0]           #(value,value text,Timestamp)
        self.timestamp = 0
        self.debug = True

    def msg(self,msg,error=0):
        """msg Method for Debug Output etc.
                Parameter:
                msg =               The Message The woutput / saved worth it
                error = 0           error = 0 Status error = 1 Error Messages"""
        if error == 0:
            if self.debug: print(":>        %s"%(msg))
        elif error == 1:
            if self.debug: print(":> Error: %s"%(msg))

    def update_statustext(self):
        """Calls all Status text to a Channel from and Give back to you as a List"""
        result = self.master.GetChannelStatTextCnt(self.channel_handle)
        if not result:
            self.statustext = 0
        if result == -1:
            self.msg("Channel handle %s invalid fur Device %s"%(self.channel_handle,self.device_handle),1)
            self.statustext = -1
        else:
            for i in range(1,result):
                self.statustext.append(self.master.GetChannelStatText(self.channel_handle,i))
        return self.statustext

    def update_value(self):
        """Channel value to update, These Method need some Sekunthe. Give the value back"""
        result = self.master.GetChannelValue(self.channel_handle,self.device_handle,5)
        #result = (0, 'no value')
        if result == -3: return result
        else:
            channeltimestamp = self.update_timestamp()
            self.value[0] = result[0]
            self.value[1] = result[1]
            self.value[2] = channeltimestamp
            return result

    def update_timestamp(self):
        """Updated the Time Stamp of Channel s and Give him back"""
        result = self.master.GetChannelValueTimeStamp(self.channel_handle)
        self.timestamp = result
        return result

    def update_range(self):
        """Updated the Channel Area and Give back as a tuple"""
        result = self.master.GetChannelValRange(self.channel_handle)
        self.range = result
        return result

    def update_name(self):
        """Updated the Name of the Channels and Give it back"""
        result = self.master.GetChannelName(self.channel_handle)
        self.name = result
        return result

    def update_unit(self):
        """Updated the Unit (kWh) of Channels and Give him back"""
        result = self.master.GetChannelUnit(self.channel_handle)
        self.unit = result
        return result

    def update_all(self,noname=0,nounit=0,nostatustext=0,novalue=1,norange=0):
        """Updated all, the complete Channel 
                Parameter:
                noname = 0          Namen des Channel s not to update
                nounit = 0          Unit des Channel s not to update
                nostatustext = 0    Status text des Channel s not to update
                novalue = 1         Wert des Channel s not to update
                norange = 0         Range of Channel s not to update
                Ergebnis:
                Tupel (name,unit,statustext,value,range)"""
        statustext = []
        value = (0,"",0)
        valrange = ()
        unit = ""
        name = ""

        if not noname: name = self.update_name()
        if not nounit: unit = self.update_unit()
        if not nostatustext: statustext = self.update_statustext()
        if not novalue: value = self.update_value()
        if not norange: valrange = self.update_range()                 # range nicht erlaubt weil wegen Schluesselwort

        return (name,unit,statustext,value,valrange)

    def get_name(self):
        """Give the Channel Name back"""
        return self.name

    def get_unit(self):
        """Give The Channel Unit back"""
        return self.unit

    def get_statustext(self):
        """Give the Channel Status text back"""
        return self.statustext

    def get_value(self):
        """Give the Channel Value back"""
        return self.value

    def get_range(self):
        """Give the Channel Value Range back"""
        return self.range

if __name__ == "__main__":
    #main = pyYASDI()
    pass
