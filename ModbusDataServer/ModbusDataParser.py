import struct
from Models import ModbusParsedData, ParsedFieldData
from JsonResult import *

class ModbusDataParser:
	CONST_ENDIAN_MAPPING = [
		{
			'endian': 'Little-Endian',
			'format': '<'
		},
		{
			'endian': 'Big-Endian',
			'format': '>'
		},
		{
			'endian': 'Mid-Little-Endian',
			'format': '<>'
		},
		{
			'endian': 'Mid-Big-Endian',
			'format': '<>'
		},
	]
	# Type Mapping, will be filled someday....
	CONST_TYPE_MAPPING = [
		{
			'format': 'c',
			'type': 'char',
			'length': 1,
		},
		{
			'format': 'h',
			'type': 'short',
			'length': 2,
		},
		{
			'format': 'i',
			'type': 'int', # signed,
			'length': 4,
		},
		{
			'format': 'f',
			'type': 'float',
			'length': 4,
		},
		{
			'format': 'd',
			'type': 'double',
			'length': 8,
		},	
	]

	# --------
	# 2026.06.01
	# Add basic parse method: Little Endian&Big Endian
	# For Rita LDA110-E
	# Basic parameters: Multipler, dataType, Field Name,Endian
	# return Result as Object: ModbusParseResult
	# To Do List:
	# Mid-Big Endian, or Custom Type
	# Which is Difficult a lot
	# -------
	# -------
	# 2026.06.02
	# trans parameter into parseInfo object and replace hexString to payload(all Data)
	# -------
	# 2026.06.05
	# Add Mid-Little-Endian And Mid-Big-Endian Basically
	# Which Probably has Problem in Future
	# Will be Checked by other power meter somedays
	# and change parameters: payload and deviceInfo
	# -------
	@classmethod
	# def parseData(cls, hexString, DataType, FieldName, Multipler, Endian):
	# def parseData(cls,payload, parseInfo):
	def parseData(cls,modbusPayload, deviceInfo):
		print(modbusPayload.data)
		payload = modbusPayload.data.Payload
		parseInfo = deviceInfo.parseInfo
		parsedData = []
		for p in parseInfo:
			startIndex = p.ResolveLocation
			endIndex = p.ResolveLocation + p.ResolveLength
			processData = payload[startIndex:endIndex]
			processData = "".join(processData)
			print(processData)
			DataType = p.DataType
			Endian = p.Endian
			FieldName = p.FieldName
			Multipler = p.Multipler
			for constType in cls.CONST_TYPE_MAPPING:
				if constType['type'] == DataType:
					for endian in cls.CONST_ENDIAN_MAPPING:
						if endian['endian'] == Endian:
							if Endian == "Mid-Little-Endian":
								# --------------
								# Mid-Little Endian: CDAB
								# Each DWord Trans And Order by Big Endian
								# Test By PA310
								# Probably has problem in future, test by other Power Meter
								# If Data Format In Double, Value Will Be Added And Returned.
								# ---------------
								dWordList = []
								payloadList = payload[startIndex:endIndex]
								for sliceNum in range(0, len(payloadList),2):
									dWordList.append(payloadList[sliceNum:sliceNum+2])
								print(dWordList)
								processValue = 0
								for rawHexValue in dWordList:
									hexString = "".join(rawHexValue[::-1])
									unpackParameter = ">f"
									unPackValue = struct.unpack(unpackParameter, bytes.fromhex(hexString))
									unPackValue = unPackValue[0]
									processValue += unPackValue
								value = processValue
							elif Endian == "Mid-Big-Endian":
								# --------------
								# Mid-Little Endian: BADC
								# Each DWord Trans by self in bit
								# And Order by Big Endian
								# Test By PA310
								# Probably has problem in future, test by other Power Meter
								# If Data Format In Double, Value Will Be Added And Returned.
								# ---------------
								dWordList = []
								payloadList = payload[startIndex:endIndex]
								for sliceNum in range(0, len(payloadList),2):
									sliceList = payloadList[sliceNum:sliceNum+2]
									sliceList = ["".join((i[:2],i[2:])[::-1]) for i in sliceList]
									dWordList.append(sliceList)
								print(dWordList)
								processValue = 0
								for rawHexValue in dWordList:
									hexString = "".join(rawHexValue)
									unpackParameter = ">f"
									unPackValue = struct.unpack(unpackParameter, bytes.fromhex(hexString))
									unPackValue = unPackValue[0]
									processValue += unPackValue
								value = processValue
							else:
								unpackParameter = endian['format'] + constType['format']
								print(f"@@@@@@unpackParameter is:{unpackParameter}")
								rawHex = bytes.fromhex(processData)
								value = struct.unpack(unpackParameter, rawHex)
								value = value[0]
							value *= Multipler
							parsedData.append(
								# ModbusParsedData(
								# 	FieldName = FieldName,
								# 	DataType = DataType,
								# 	Multipler = Multipler,
								# 	Value = value,
								# 	hexValue = processData,
								# 	Endian = Endian
								# )
								ParsedFieldData(
									value = value,
									hexValue = processData,
									parseInfo = p,
								)
								# ModbusParsedData(
								# 	PayloadTime = modbusPayload.PayloadTime,
								# 	value = value,
								# 	hexValue = processData,
								# 	DeviceInfo = deviceInfo
								# )
							)
							break
		# return parsedData
		return ModbusParsedData(
			PayloadTime = modbusPayload.data.PayloadTime,
			parsedData = parsedData,
			DeviceInfo = deviceInfo
		)