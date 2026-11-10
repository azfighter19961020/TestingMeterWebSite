from django.contrib.auth.hashers import check_password as verify_password
from django.contrib.auth.hashers import make_password
from django.db import models


class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=10)
    password = models.CharField(max_length=256)
    email = models.CharField(max_length=25)
    phone_number = models.CharField(max_length=15, db_column='phoneNumber')
    address = models.CharField(max_length=25)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return verify_password(raw_password, self.password)


class MeterData(models.Model):
    id = models.AutoField(primary_key=True)
    Time = models.BigIntegerField()
    rPhaseVoltage = models.FloatField()
    sPhaseVoltage = models.FloatField()
    tPhaseVoltage = models.FloatField()
    rPhaseCurrent = models.FloatField()
    sPhaseCurrent = models.FloatField()
    tPhaseCurrent = models.FloatField()
    Factor = models.FloatField()
    TotalkWh = models.FloatField()
    DeviceName = models.CharField(max_length=25)
