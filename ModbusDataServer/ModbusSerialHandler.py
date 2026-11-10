from pymodbus.client import ModbusSerialClient
import time
import json
from datetime import datetime
from Models import *
from JsonResult import *
from ModbusDataParser import ModbusDataParser

class ModbusSerialHandler:
	# ----------
	# class for handle Modbus things: open serial communcation, testing devices, and getData/parse data through parser
	# 2026.06.05
	# change settings to read json file and get/parse parameters to deviceInfo
	# which will bring PayloadTime and Device unique keys to Frontend
	# make sure data can be show and store correctly
	# ----------
	def __init__(self):
		self.modbusClient = None
	def connectToSerial(self,modbusSettings):
		self.modbusClient = ModbusSerialClient(**modbusSettings)
		try:
			self.modbusClient.connect()
		except Exception as e:
			return JsonResult(ResultStatus.FAIL, "Connect Modbus Client Failed.")
		else:
			return JsonResult(ResultStatus.OK, "Modbus Client Connected.")
	def testModbusDevice(self, deviceInfo):
		pass
	def getModbusData(self,deviceInfo):
		nowTime = datetime.now().timestamp()
		if not self.modbusClient:
			return JsonResult(ResultStatus.FAIL, "Modbus Client is not connected.")
		try:
			modbusCommand = deviceInfo.command
			deviceID = modbusCommand.deviceID
			functionCode = modbusCommand.functionCode
		except:
			return JsonResult(ResultStatus.FAIL, "Lack of neccessary parameters.")
		payload = []
		for reg in modbusCommand.registers:
			time.sleep(5)
			try:
				if functionCode == 3:
					response = self.modbusClient.read_holding_registers(address = reg.address,count = reg.count,device_id = deviceID)
				elif functionCode == 4:
					response = self.modbusClient.read_input_registers(address = reg.address,count = reg.count,device_id = deviceID)
				result = response.registers
			except Exception as e:
				data = ModbusPayload(
					PayloadTime = nowTime,
					Payload = "Get Modbus Data Failed.",
					DeviceInfo = deviceInfo
				)
				return JsonResult(ResultStatus.FAIL, f"Read Modbus Data Failed. Function Code: {functionCode}. err{str(e)}", data)
			for res in result:
				hexRes = "{:04x}".format(res)
				payload.append(hexRes)
		# return ModbusPayload(
		# 	PayloadTime = nowTime,
		# 	Payload = payload,
		# 	DeviceInfo = deviceInfo
		# )
		data = ModbusPayload(
			PayloadTime = nowTime,
			Payload = payload,
			DeviceInfo = deviceInfo
		)
		return JsonResult(ResultStatus.OK, "Get Modbus Data Success.", data)
	# def parseModbusData(self,hexString,DataType,FieldName,Multipler,Endian):
	# def parseModbusData(self,payload, parseInfo):
	def parseModbusData(self,modbusPayload, deviceInfo): 
		# resolved_data = ModbusDataParser.parseData(hexString,DataType,FieldName,Multipler,Endian)
		# resolved_data = ModbusDataParser.parseData(payload,parseInfo)
		resolved_data = ModbusDataParser.parseData(modbusPayload,deviceInfo)
		if resolved_data:
			# return {
			# 	"status": 0,
			# 	"message": "Modbus Data Resolved.",
			# 	"data": resolved_data,
			# }
			return JsonResult(ResultStatus.OK, "Modbus Data Resolved.", resolved_data)
		# return {
		# 	"status": 1,
		# 	"message": "resolve Modbus Data Failed."
		# }
		return JsonResult(ResultStatus.FAIL, "Resolve Modbus Data Failed.")

if __name__ == "__main__":
	print("Modbus Handler test.")
	with open("customer.json",'r', encoding = "utf-8") as file:
		devices = json.loads(file.read())
	testDevice = devices[0]
	testDevice = DeviceInfo().fromJSON(testDevice)

	with open("modbusSettings.json", encoding = "utf-8") as file:
		ModbusSettings = json.loads(file.read())

	# deviceID = 1
	# fuctionCode = 3
	# registers = [
	# 	# {'address'1016:,'count':3}
	# 	Register(
	# 		address = 1016,
	# 		count = 3
	# 	)
	# ]

	# command = ModbusCommand(
	# 	deviceID = deviceID,
	# 	functionCode = fuctionCode,
	# 	registers = registers
	# )

	# command = ModbusCommand().fromJSON(testDevice['ModbusCommand'])

	# print(command)
	print(testDevice.command)

	# for reg in command.registers:
		# print(reg)
	for reg in testDevice.command.registers:
		print(reg)

	# parseInfos = []
	# for p in testDevice['parseInfo']:
		# parseInfos.append(ParseInfo().fromJSON(p))
	for p in testDevice.parseInfo:
		print(p)

	

	# comPort = "COM6"
	# baudRate = 9600
	# stopBits = 1
	# byteSize = 8
	# parity = 'N'
	# timeout = 15
	# ModbusSettings = {
	# 	'port': comPort,
	# 	'baudrate': baudRate,
	# 	'stopbits': stopBits,
	# 	'bytesize': byteSize,
	# 	'parity': parity,
	# 	'timeout': timeout
	# }
	Handler = ModbusSerialHandler()
	result = Handler.connectToSerial(ModbusSettings)
	print(result)
	# ModbusPayload = Handler.getModbusData(testDevice.command)
	modbusPayload = Handler.getModbusData(testDevice)
	print(modbusPayload)
	# # catch status, will throw error or be Object some day
	# # FieldData, Endian ..... e.t.c will be Object some day too.
	# resolveRData = Handler.parseModbusData(ModbusPayload[0],'short','R Phase Voltage',0.1,'Big-Endian')
	# resolveSData = Handler.parseModbusData(ModbusPayload[1],'short','S Phase Voltage',0.1,'Big-Endian')
	# resolveTData = Handler.parseModbusData(ModbusPayload[2],'short','T Phase Voltage',0.1,'Big-Endian')
	# if not resolveRData['status']:
	# 	print(resolveRData['data'])
	# 	print(resolveSData['data'])
	# 	print(resolveTData['data'])
	# result = Handler.parseModbusData(payloadInfo,DataPacketInfo)
	# print(result)
	# for key,value in result['data']['fieldData'].items():
		# print(f"field: {key}, value: {value['value']}")

	# result = Handler.parseModbusData(ModbusPayload, testDevice.parseInfo)
	result = Handler.parseModbusData(modbusPayload, testDevice)
	print(result.data)

	