from ModbusSerialHandler import ModbusSerialHandler
import json
from Models import *
from JsonResult import *

class DataHandler:
    def __init__(self):
        self.customerJSON = None
        self.modbusHandler = ModbusSerialHandler()
        self.modbusDevices = []
        self.modbusDeviceStatus = []
        self.modbusSettings = {}
    def initialize(self):
        with open("customer.json",'r', encoding = "utf-8") as file:
            devices = json.loads(file.read())
            for d in devices:
                self.modbusDevices.append(DeviceInfo().fromJSON(d))
        with open("modbusSettings.json",'r', encoding = "utf-8") as file:
            self.modbusSettings = json.loads(file.read())
        try:
            self.modbusHandler.connectToSerial(self.modbusSettings)
        except Exception as e:
            return JsonResult(ResultStatus.FAIL, "initialize Failed. check Modbus Settings or Modbus Equipments.")
        else:
            return JsonResult(ResultStatus.OK, "initialize success.")
    def deviceAlive(self):
        pass
    def getData(self):
        deviceData = []
        for device in self.modbusDevices:
            result = self.modbusHandler.getModbusData(device)
            if result.status == ResultStatus.FAIL:
                if "Read" not in result.message:
                    return result
                else:
                    deviceData.append(result)
            else:
                resolveData = self.modbusHandler.parseModbusData(result.data,device)
                deviceData.append(resolveData)
        return JsonResult(ResultStatus.OK, "Get Modbus Data Complete.", deviceData)

if __name__ == '__main__':
    DataHDR = DataHandler()
    init = DataHDR.initialize()
    for d in DataHDR.modbusDevices:
        print(d)
    print(DataHDR.modbusSettings)
    print(init)
    collectedData = DataHDR.getData()
    if collectedData.status == ResultStatus.OK:
        for data in collectedData.data:
            result = data.data
            print(result.DeviceInfo.DeviceLocation)
            print(result.DeviceInfo.DeviceUniqueName)
            if data.status == ResultStatus.OK:
                for resolvedData in result.parsedData:
                    print(resolvedData)
            else:
                print(data.message)
