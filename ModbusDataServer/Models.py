#-----------------------------------------------------------
# Basic Class: Command, Resolve Method And DeviceInfo
# Key: DeviceUniqueName
#-----------------------------------------------------------
class ModbusCommand:
	def __init__(self,deviceID = 1,functionCode = 3,registers = None):
		self.deviceID = deviceID
		self.functionCode = functionCode
		self.registers = registers
	def fromJSON(self,JSON):
		self.deviceID = JSON['deviceID']
		self.functionCode = JSON['functionCode']
		self.registers = []
		for reg in JSON['registers']:
			self.registers.append(Register().fromJSON(reg))
		return self
	def __str__(self):
		return f"ModbusCommand[deviceID={self.deviceID},functionCode={self.functionCode},hasRegisters={self.registers}]"

class Register:
	def __init__(self,address = 0,count = 0):
		self.address = address
		self.count = count
	def fromJSON(self,JSON):
		self.address = JSON['address']
		self.count = JSON['count']
		return self
	def __str__(self):
		return f"Register[address={self.address},count={self.count}]"

class ParseInfo:
	def __init__(self, ResolveLocation = 0, ResolveLength = 0, DataType = "", Endian = "", Multipler = 0, FieldName = ""):
		self.ResolveLocation = ResolveLocation
		self.ResolveLength = ResolveLength
		self.DataType = DataType
		self.Endian = Endian
		self.Multipler = Multipler
		self.FieldName = FieldName
	def fromJSON(self,JSON):
		self.ResolveLocation = JSON['ResolveLocation']
		self.ResolveLength = JSON['ResolveLength']
		self.DataType = JSON['DataType']
		self.Endian = JSON['Endian']
		self.Multipler = JSON['Multipler']
		self.FieldName = JSON['FieldName']
		return self
	def __str__(self):
		return f"ParseInfo[ResolveLocation={self.ResolveLocation},ResolveLength={self.ResolveLength}, DataType={self.DataType},Endian={self.Endian}, Multipler={self.Multipler},FieldName={self.FieldName}]"

class DeviceInfo:
	def __init__(self,DeviceLocation = "", DeviceUniqueName = "", Description = "",command = None, parseInfo = None):
		self.DeviceLocation = DeviceLocation
		self.DeviceUniqueName = DeviceUniqueName
		self.Description = Description
		self.command = command
		self.parseInfo = parseInfo
	def fromJSON(self,JSON):
		self.DeviceLocation = JSON['DeviceLocation']
		self.DeviceUniqueName = JSON['DeviceUniqueName']
		self.Description = JSON['Description']
		deviceInfo = JSON['DeviceInfo']
		self.command = ModbusCommand().fromJSON(deviceInfo['ModbusCommand'])
		self.parseInfo = []
		for p in deviceInfo['parseInfo']:
			self.parseInfo.append(ParseInfo().fromJSON(p))
		return self
	def __eq__(self, other):
		if type(self) == type(other):
			return self.DeviceUniqueName == other.DeviceUniqueName
		return False
	def __str__(self):
		returnString = ""
		returnString += "@@@@Modbus Device@@@@\n"
		returnString += f"DeviceLocation: {self.DeviceLocation}\n"
		returnString += f"DeviceUniqueName: {self.DeviceUniqueName}\n"
		returnString += f"Description: {self.Description}\n"
		returnString += f"Modbus Device ID: {self.command.deviceID}\n"
		returnString += f"Modbus Function Code: {self.command.functionCode}\n"
		for reg in self.command.registers:
			returnString +=  str(reg) + "\n"
		for p in self.parseInfo:
			returnString += str(p) + "\n"
		returnString += "@@@@@@@@@@@@@@@@"
		return returnString




#-----------------------------------------------------------
# Result Class: Payload And Resolved Data
# Key: DeviceUniqueName
# Trans By DeviceInfo
#-----------------------------------------------------------

class ModbusPayload:
	# ----------
	# Result Class For Modbus DeviceData
	# Including DeviceInfo For Recongize Parent
	# ----------
	def __init__(self, PayloadTime = 0, Payload = [], DeviceInfo = None):
		self.PayloadTime = PayloadTime
		self.Payload = Payload
		self.DeviceInfo = DeviceInfo
	def __str__(self):
		returnString = ""
		returnString += "@@@@@@@@@@@@@@@"
		returnString += f"PayloadTime: {self.PayloadTime}\n"
		payload = "".join(self.Payload)
		returnString += f"Payload: {payload}\n"
		returnString += str(self.DeviceInfo)
		return returnString


class ParsedFieldData:
	# ----------
	# 2026.06.05 New Result Class
	# Sub Class For ModbusParsedData
	# For Normal Situation, this SHOULD NOT be alone returned
	# ----------
	def __init__(self, value = 0, hexValue = "", parseInfo = None):
		self.value = value
		self.hexValue = hexValue
		self.parseInfo = parseInfo
	def __str__(self):
		returnString = "parseInfo: \n"
		returnString += str(self.parseInfo)
		returnString += f"\n value: {self.value}\n"
		returnString += f"hexValue: {self.hexValue} \n"
		return returnString

class ModbusParsedData:
	# def __init__(self, FieldName = "",Endian = '', DataType = "", Multipler = "", Value = 0, hexValue = ""):
	# def __init__(self, PayloadTime = 0, value = 0, hexValue = 0, DeviceInfo = None):
	# -----------
	# Result class: parsed data
	# which contains one modbus devices all field data
	# and origin hex value from serial handler
	# 2026.06.05
	# a lot of adjust: include constructure adjust
	# make deviceInfo not be duplicated
	# and make sure one device to one ModbusParsedData
	# -----------
	def __init__(self,PayloadTime = 0, parsedData = [], DeviceInfo = None):
		self.PayloadTime = PayloadTime
		self.parsedData = parsedData
		# self.value = value
		# self.hexValue = hexValue
		self.DeviceInfo = DeviceInfo
		# self.FieldName = FieldName
		# self.DataType = DataType
		# self.Multipler = Multipler
		# self.Value = Value
		# self.hexValue = hexValue
		# self.Endian = Endian
	def __str__(self):
		# return f"ModbusParsedData[FieldName={self.FieldName},Endian = {self.Endian},DataType={self.DataType},Multipler={self.Multipler},Value={self.Value},hexValue={self.hexValue}]"
		returnString = ""
		returnString += "@@@@@@@@@@@@@@@"
		returnString += f"PayloadTime: {self.PayloadTime}\n"
		for fieldData in self.parsedData:
			returnString +=  str(fieldData)
			returnString += "\n"
		returnString += str(self.DeviceInfo)
		return returnString

	