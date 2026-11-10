from django.urls import path
from . import views
urlpatterns = [
    # path('', views.home, name='home'),

    path('', views.loginPage, name='login_page'),
    path('home/', views.home, name='home'),
    path('liveValue/', views.liveValue, name='live_value'),
    path('kWhRange/', views.kWhRange, name='kwh_range'),
    # path('loginPage/', views.loginPage, name='login_page'),
    path('login/', views.login, name='login'),
    path('addUser/', views.addUser, name='add_user'),
    path('addMeterdata/', views.addMeterData, name='add_meter_data'),
    path('getMeterData/', views.getMeterData, name='get_meter_data'),
    path('getTotalkWh/', views.getTotalkWh, name='get_total_kwh'),
    path('getKWhRangeData/', views.getKWhRangeData, name='get_kwh_range_data'),
    path('getDeviceName/', views.getDeviceName, name='get_device_name'),
]
