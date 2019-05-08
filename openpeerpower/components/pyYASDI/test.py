import ctypes,array       #ctypes laed die Libs in Python, array (BuildIn) fuer C Arrays

# load yasdimaster DLL
#  DWORD - 32 bit unsigned -> ctypes.c_ulong()
#  Word  - 16 bit unsigned -> ctypes_c_ushort()
#  Byte  - 8  bit unsigned -> 'ctypes.c_byte()
# yasdiMasterInitialize( char * cIniFileName, DWORD * pDriverCount)
# yasdiMaster = ctypes.cdll.LoadLibrary("./yasdimaster")

yasdiMaster = ctypes.cdll.LoadLibrary("yasdimaster")
#yasdiMaster = ctypes.cdll.LoadLibrary(r"C:\Users\Paul\Documents\github\OpenPeerPower\SMA\yasdi-1.8.1build9-src\projects\generic-cmake\build-mingw\Debug\yasdimaster")
# Initialise Yasdi
DriverCount = ctypes.c_ulong()
pDriverCount = ctypes.byref(DriverCount)
Ini_file = b"C:\Users\Paul\Documents\github\OpenPeerPower\pyYASDI\yasdi.ini"
#Ini_file = ctypes.c_wchar_p(r"C:\Users\Paul\Documents\github\OpenPeerPower\pyYASDI\yasdi.ini")
#Ini_file = ctypes.c_wchar_p(b"C:/Windows/SysWOW64/yasdi.ini")
# Ires = yasdiMaster.yasdiMasterInitialize(Ini_file, pDriverCount)
# Ires = yasdiMaster.yasdiMasterInitialize(None, pDriverCount)
#yasdiMaster.yasdiMasterInitialize.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
#Ires = yasdiMaster.yasdiMasterInitialize(Ini_file, pctypes.byref(DriverCount))
Ires = yasdiMaster.yasdiMasterInitialize(Ini_file, pDriverCount)
#Ires = yasdiMaster.yasdiMasterInitialize(None, pDriverCount)
# Return all interface drivers which YASDI recognizes
# and activate as necessary... */ 
yasdi = ctypes.cdll.LoadLibrary("yasdi")
# DWORD yasdiGetDriver(DWORD * DriverIDArray, int maxDriverIDs); 
# DriverIDArray = array.array('L',[0]*3)
# DriverIDArray = ctypes.Array(3, ctypes.c_long(0))
DriverIDArray = (ctypes.c_long * 6)()
#pDriverIDArray = ctypes.pointer(DriverIDArray)
pDriverIDArray = ctypes.byref(DriverIDArray)
maxDriverIDs = ctypes.c_int(3)
# xpDriverIDArray = ctypes.pointer(DriverIDArray)
#yasdi.argtypes = [ctypes.POINTER(ctypes.c_long), ctypes.c_int]

#result = yasdi.yasdiGetDriver(ctypes.byref(DriverIDArray), ctypes.c_int(3))
result = yasdi.yasdiGetDriver(pDriverIDArray, ctypes.c_int(3))

#c yasdiSetDriverOnline(...)
driverID = ctypes.c_ulong(0)
pdriverID  = ctypes.byref(driverID)
#DriverNameBuffer = ctypes.c_char_p(b" "*30)
DriverNameBuffer = b" "*30
#pDriverNameBuffer  = ctypes.pointer(DriverNameBuffer)
LenBuffer = ctypes.c_ulong(30)
pLenBuffer  = ctypes.byref(LenBuffer)
bytesret = yasdi.yasdiGetDriverName(driverID, DriverNameBuffer, 30)
res = yasdi.yasdiSetDriverOnline(driverID)
# Search for all connected devices (one, in this case)
resu = yasdiMaster.yasdiDoMasterCmdEx(b"detect", 1, None, None)
# Get all device handles

DeviceHandles = (ctypes.c_long * 5)()
pDeviceHandles = ctypes.byref(DeviceHandles)
resul = yasdiMaster.GetDeviceHandles(pDeviceHandles, 5)

DeviceID = ctypes.c_ulong(1)
pDeviceID  = ctypes.byref(DeviceID)
DeviceNameBuffer = b" "*30
# result = yasdiMaster.GetDeviceName( DWORD DevHandle, char * DestBuffer, int len)
result = yasdiMaster.GetDeviceName(1, DeviceNameBuffer, 30)
# Get all channel handles for this device
#c GetChannelHandles(...)
iChannelHandleCount = 50
ChannelHandles = (ctypes.c_long * iChannelHandleCount)()
pChannelHandles = ctypes.byref(ChannelHandles)
devhandle = DeviceHandles[0]
HandleCount = yasdiMaster.GetChannelHandlesEx(devhandle, pChannelHandles, iChannelHandleCount, None)
ChannelNameBuffer = b" "*30
#pDriverNameBuffer  = ctypes.pointer(DriverNameBuffer)
LenChannelNameBuffer = ctypes.c_ulong(30)
#pLenBuffer  = ctypes.pointer(LenBuffer)
pLenChannelNameBuffer  = ctypes.byref(LenChannelNameBuffer)
dblValue = ctypes.c_double(0)
pdblValue = ctypes.byref(dblValue)
ValText = b" "*30
LenValText = ctypes.c_ulong(30)

max_val_age = ctypes.c_ulong(10)
for i in range(HandleCount):
    res = yasdiMaster.GetChannelName(ChannelHandles[i], ChannelNameBuffer, LenChannelNameBuffer)
    print(ChannelNameBuffer)
    #result = yasdiMaster.GetChannelValue(ChannelHandles[i], devhandle, pDevValue, ValText, pValText, max_val_age)
    result = yasdiMaster.GetChannelValue(ChannelHandles[i], devhandle, pdblValue, ValText, LenValText, max_val_age)
    print(dblValue)

#SHARED_FUNCTION DWORD GetChannelHandlesEx(DWORD pdDevHandle,
#                                          DWORD * pdChanHandles,
#                                          DWORD dMaxHandleCount,
#                                          TChanType chanType
#                                          )
# Request or set channel values
#c While( youWant ) 
#c {  SetChannelValue(...) or  GetChannelValue(...) } 
# Deactivate all utilized interfaces
#c yasdiSetDriverOffline(...) 
# Shut down YASDI
yasdiMaster.yasdiMasterShutdown() 