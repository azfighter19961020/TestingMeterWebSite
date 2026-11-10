from enum import Enum

class ResultStatus(Enum):
	OK = 200
	FAIL = 500

class JsonResult:
	def __init__(self, status = ResultStatus.OK, message = "", data = None):
		self.status = status
		self.message = message
		self.data = data
	def __str__(self):
		return str(self.__dict__)