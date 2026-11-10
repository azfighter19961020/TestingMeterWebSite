from ModbusSerialHandler import ModbusSerialHandler
from Models import *
import requests
import time
import json


with open("customer.json",'r', encoding = "utf-8") as file:
	devices = json.loads(file.read())
# testDevice = devices[0]
# testDevice = DeviceInfo().fromJSON(testDevice)

with open("modbusSettings.json", encoding = "utf-8") as file:
	ModbusSettings = json.loads(file.read())


superUserId = "backuser"
superUserPassword = "a123456789123"
SERVER_IP = "http://127.0.0.1:8000"
SERVER_URL = "/testapp/addMeterdata/"

BASE_JSON = {
	"username": superUserId,
	"password": superUserPassword
}

Handler = ModbusSerialHandler()
result = Handler.connectToSerial(ModbusSettings)

print("======Modbus Handler connect result======")
print(result)


while True:
	for Device in devices:

		modbusPayload = Handler.getModbusData(DeviceInfo().fromJSON(Device))
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
		result = Handler.parseModbusData(modbusPayload, DeviceInfo().fromJSON(Device))
		# print(result.data)
		if result.data is not None:
			returnData = {}
			for fieldData in result.data.parsedData:
				returnData[fieldData.parseInfo.FieldName] = fieldData.value
			returnData['Time'] = int(result.data.PayloadTime*1000)
			returnData['DeviceName'] = Device['DeviceLocation']
			# data = result.data
			returnData.update(BASE_JSON)
			print(returnData)
			# data.update({"Time": int(time.time()*1000)})
			postResult = requests.post(SERVER_IP+SERVER_URL, json = returnData)
			print(postResult.text)
	time.sleep(60 * 5)
