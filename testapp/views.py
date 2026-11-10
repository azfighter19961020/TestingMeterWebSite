import json
import math

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import MeterData, User


def home(request):
    return render(request, 'testapp/home.html')


def liveValue(request):
    return render(request, 'testapp/liveValue.html')


def kWhRange(request):
    return render(request, 'testapp/kWhRange.html')


def loginPage(request):
    return render(request, 'testapp/login.html')


def _read_json(request):
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, JsonResponse({'error': 'Request body must be valid JSON.'}, status=400)

    if not isinstance(data, dict):
        return None, JsonResponse({'error': 'JSON body must be an object.'}, status=400)
    return data, None


def _logged_in_user(request):
    user_id = request.session.get('testapp_user_id')
    if user_id is None:
        return None
    return User.objects.filter(id=user_id).first()


@require_POST
@csrf_exempt
def login(request):
    data, error = _read_json(request)
    if error:
        return error

    username = data.get('username')
    password = data.get('password')
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({'error': 'username and password must be strings.'}, status=400)

    user = User.objects.filter(username=username).first()
    if user is None or not user.check_password(password):
        return JsonResponse({'error': 'Invalid username or password.'}, status=401)

    request.session.cycle_key()
    request.session['testapp_user_id'] = user.id
    return JsonResponse({'message': 'Login Successful', 'user_id': user.id})


@require_POST
@csrf_exempt
def addUser(request):
    data, error = _read_json(request)
    if error:
        return error

    fields = ('username', 'password', 'email', 'phone_number', 'address')
    if any(not isinstance(data.get(field), str) for field in fields):
        return JsonResponse({'error': 'All user fields must be provided as strings.'}, status=400)
    if any(not data[field] for field in fields):
        return JsonResponse({'error': 'User fields cannot be empty.'}, status=400)
    if len(data['username']) > 10 or len(data['email']) > 25:
        return JsonResponse({'error': 'username or email exceeds its maximum length.'}, status=400)
    if len(data['phone_number']) > 15 or len(data['address']) > 25:
        return JsonResponse({'error': 'phone_number or address exceeds its maximum length.'}, status=400)
    if User.objects.filter(username=data['username']).exists():
        return JsonResponse({'error': 'That username is already registered.'}, status=409)

    user = User(
        username=data['username'],
        email=data['email'],
        phone_number=data['phone_number'],
        address=data['address'],
    )
    user.set_password(data['password'])
    user.save()
    return JsonResponse({'message': 'User created.', 'user_id': user.id}, status=201)


@require_POST
@csrf_exempt
def addMeterData(request):
    data, error = _read_json(request)
    if error:
        return error

    username = data.get('username')
    password = data.get('password')
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({'error': 'username and password must be provided as strings.'}, status=400)

    user = User.objects.filter(username=username).first()
    if user is None or not user.check_password(password):
        return JsonResponse({'error': 'Invalid username or password.'}, status=401)

    integer_fields = ('Time',)
    float_fields = (
        'rPhaseVoltage', 'sPhaseVoltage', 'tPhaseVoltage',
        'rPhaseCurrent', 'sPhaseCurrent', 'tPhaseCurrent',
        'Factor', 'TotalkWh',
    )
    required_fields = (*integer_fields, *float_fields, 'DeviceName')
    if any(field not in data for field in required_fields):
        return JsonResponse({'error': 'All meter data fields are required.'}, status=400)
    if isinstance(data['Time'], bool) or not isinstance(data['Time'], int):
        return JsonResponse({'error': 'Time must be an integer.'}, status=400)
    if not isinstance(data['DeviceName'], str) or not data['DeviceName']:
        return JsonResponse({'error': 'DeviceName must be a non-empty string.'}, status=400)
    if len(data['DeviceName']) > 25:
        return JsonResponse({'error': 'DeviceName must be at most 25 characters.'}, status=400)

    values = {}
    for field in float_fields:
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return JsonResponse({'error': f'{field} must be a number.'}, status=400)
        if not math.isfinite(value):
            return JsonResponse({'error': f'{field} must be finite.'}, status=400)
        values[field] = value

    meter_data = MeterData.objects.create(
        Time=data['Time'],
        DeviceName=data['DeviceName'],
        **values,
    )
    return JsonResponse({'message': 'Meter data created.', 'id': meter_data.id}, status=201)


@require_GET
def getMeterData(request):
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    records = list(MeterData.objects.values(
        'id', 'Time', 'rPhaseVoltage', 'sPhaseVoltage', 'tPhaseVoltage',
        'rPhaseCurrent', 'sPhaseCurrent', 'tPhaseCurrent', 'Factor',
        'TotalkWh', 'DeviceName',
    ))
    for record in records:
        record['Time'] /= 1000

    return JsonResponse({'data': records})


@require_GET
def getTotalkWh(request):
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    records = MeterData.objects.order_by('DeviceName', '-Time', '-id').values(
        'DeviceName', 'Time', 'TotalkWh',
    )
    latest_by_device = {}
    for record in records:
        latest_by_device.setdefault(record['DeviceName'], record)

    latest_time = max(
        (record['Time'] for record in latest_by_device.values()),
        default=None,
    )
    total_kwh = sum(record['TotalkWh'] for record in latest_by_device.values())

    return JsonResponse({
        'Time': latest_time / 1000 if latest_time is not None else None,
        'TotalkWh': total_kwh,
    })


@require_GET
def getKWhRangeData(request):
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    device_name = request.GET.get('DeviceName', '').strip()
    start_time = request.GET.get('startTime', '')
    end_time = request.GET.get('endTime', '')
    if not device_name or len(device_name) > 25:
        return JsonResponse({'error': 'DeviceName is required and must be at most 25 characters.'}, status=400)

    try:
        start_time = int(start_time)
        end_time = int(end_time)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'startTime and endTime must be integer Unix timestamps in milliseconds.'}, status=400)

    if start_time < 0 or end_time < 0:
        return JsonResponse({'error': 'Time range values cannot be negative.'}, status=400)
    if start_time > end_time:
        return JsonResponse({'error': 'startTime must be earlier than or equal to endTime.'}, status=400)

    records = list(
        MeterData.objects.filter(
            DeviceName=device_name,
            Time__gte=start_time,
            Time__lte=end_time,
        )
        .order_by('Time', 'id')
        .values('DeviceName', 'Time', 'TotalkWh')
    )
    return JsonResponse({'data': records})


@require_GET
def getDeviceName(request):
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    device_names = list(
        MeterData.objects.order_by('DeviceName')
        .values_list('DeviceName', flat=True)
        .distinct()
    )
    return JsonResponse({'data': device_names})
