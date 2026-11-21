import json
import math

from django.db.models import Max, OuterRef, Subquery, Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import MeterData, User

MAX_BIGINT = 2 ** 63 - 1  # upper bound of MeterData.Time (BigIntegerField)


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
    if not 0 <= data['Time'] <= MAX_BIGINT:
        return JsonResponse({'error': 'Time must be a non-negative Unix timestamp in milliseconds.'}, status=400)
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


METER_DATA_FIELDS = (
    'id', 'Time', 'rPhaseVoltage', 'sPhaseVoltage', 'tPhaseVoltage',
    'rPhaseCurrent', 'sPhaseCurrent', 'tPhaseCurrent', 'Factor',
    'TotalkWh', 'DeviceName',
)
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


def _optional_int(params, name, default=None):
    """Parse an optional integer query parameter; returns (value, error_message)."""
    raw = params.get(name, '').strip()
    if raw == '':
        return default, None
    try:
        return int(raw), None
    except ValueError:
        return None, f'{name} must be an integer.'


def _latest_per_device(queryset):
    """Narrow a MeterData queryset to the newest record (by Time, then id) of each device."""
    newest_id = (
        queryset.filter(DeviceName=OuterRef('DeviceName'))
        .order_by('-Time', '-id')
        .values('id')[:1]
    )
    return queryset.filter(id=Subquery(newest_id))


@require_GET
def getMeterData(request):
    """
    Query parameters (all optional):
      DeviceName  exact device name (max 25 chars)
      startTime   inclusive lower bound, Unix timestamp in milliseconds
      endTime     inclusive upper bound, Unix timestamp in milliseconds
      latest      "1" to return only the newest record per device
      page        1-based page number (default 1)
      pageSize    records per page (default 100, max 500)

    Records are ordered newest first (or by DeviceName when latest=1).
    Returned Time values are in seconds.
    """
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    params = request.GET
    device_name = params.get('DeviceName', '').strip()
    if len(device_name) > 25:
        return JsonResponse({'error': 'DeviceName must be at most 25 characters.'}, status=400)

    start_time, error = _optional_int(params, 'startTime')
    if error is None:
        end_time, error = _optional_int(params, 'endTime')
    if error is None:
        page, error = _optional_int(params, 'page', 1)
    if error is None:
        page_size, error = _optional_int(params, 'pageSize', DEFAULT_PAGE_SIZE)
    if error:
        return JsonResponse({'error': error}, status=400)

    if (start_time is not None and start_time < 0) or (end_time is not None and end_time < 0):
        return JsonResponse({'error': 'Time range values cannot be negative.'}, status=400)
    if start_time is not None and end_time is not None and start_time > end_time:
        return JsonResponse({'error': 'startTime must be earlier than or equal to endTime.'}, status=400)
    if page < 1:
        return JsonResponse({'error': 'page must be at least 1.'}, status=400)
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        return JsonResponse({'error': f'pageSize must be between 1 and {MAX_PAGE_SIZE}.'}, status=400)

    latest = params.get('latest', '').strip().lower()
    if latest not in ('', '0', '1', 'true', 'false'):
        return JsonResponse({'error': 'latest must be 1 or 0.'}, status=400)
    latest = latest in ('1', 'true')

    filtered = MeterData.objects.all()
    if device_name:
        filtered = filtered.filter(DeviceName=device_name)
    if start_time is not None:
        filtered = filtered.filter(Time__gte=start_time)
    if end_time is not None:
        filtered = filtered.filter(Time__lte=end_time)

    if latest:
        queryset = _latest_per_device(filtered).order_by('DeviceName')
    else:
        queryset = filtered.order_by('-Time', '-id')

    total = queryset.count()
    total_pages = max(1, math.ceil(total / page_size))
    offset = (page - 1) * page_size
    # Skip the query past the last page: a huge OFFSET is invalid SQL.
    records = [] if offset >= total else list(
        queryset.values(*METER_DATA_FIELDS)[offset:offset + page_size]
    )
    for record in records:
        record['Time'] /= 1000

    return JsonResponse({
        'data': records,
        'page': page,
        'pageSize': page_size,
        'total': total,
        'totalPages': total_pages,
    })


@require_GET
def getTotalkWh(request):
    if _logged_in_user(request) is None:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    # TotalkWh is a cumulative meter reading, so the plant total is the sum of
    # each device's newest reading (the same rows as getMeterData?latest=1).
    totals = _latest_per_device(MeterData.objects.all()).aggregate(
        latest_time=Max('Time'),
        total_kwh=Sum('TotalkWh'),
    )
    latest_time = totals['latest_time']

    # Both are null when there is no meter data.
    return JsonResponse({
        'Time': latest_time / 1000 if latest_time is not None else None,
        'TotalkWh': totals['total_kwh'],
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
