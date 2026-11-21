import json

from django.test import TestCase
from django.urls import reverse

from .models import MeterData, User
from .views import MAX_BIGINT


def make_user(username='tester', password='pw'):
    user = User(username=username, email='t@example.com', phone_number='1', address='a')
    user.set_password(password)
    user.save()
    return user


def make_record(device, time_ms, kwh=1.0):
    return MeterData.objects.create(
        Time=time_ms, DeviceName=device, TotalkWh=kwh,
        rPhaseVoltage=220, sPhaseVoltage=220, tPhaseVoltage=220,
        rPhaseCurrent=1, sPhaseCurrent=1, tPhaseCurrent=1, Factor=0.9,
    )


class LoggedInTestCase(TestCase):
    """Creates a user and logs the test client in via the session."""

    def setUp(self):
        self.user = make_user()
        session = self.client.session
        session['testapp_user_id'] = self.user.id
        session.save()

    def post_json(self, url, data):
        body = data if isinstance(data, (str, bytes)) else json.dumps(data)
        return self.client.post(url, body, content_type='application/json')


# --------------------------------------------------------------------------- pages

class PageViewTests(TestCase):
    def test_pages_render_their_templates(self):
        for name, template in (
            ('login_page', 'testapp/login.html'),
            ('home', 'testapp/home.html'),
            ('live_value', 'testapp/liveValue.html'),
            ('kwh_range', 'testapp/kWhRange.html'),
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_home_calls_total_kwh_and_shows_failure_text(self):
        page = self.client.get(reverse('home')).content.decode()
        self.assertIn(reverse('get_total_kwh'), page)
        self.assertIn('載入失敗', page)


# --------------------------------------------------------------------------- login

class LoginTests(LoggedInTestCase):
    def setUp(self):
        self.user = make_user()  # not logged in
        self.url = reverse('login')

    def test_success_logs_in(self):
        response = self.post_json(self.url, {'username': 'tester', 'password': 'pw'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'message': 'Login Successful', 'user_id': self.user.id})
        self.assertEqual(self.client.session['testapp_user_id'], self.user.id)
        # The session now unlocks the protected endpoints.
        self.assertEqual(self.client.get(reverse('get_device_name')).status_code, 200)

    def test_session_key_is_rotated(self):
        self.client.get(reverse('home'))
        session = self.client.session
        session['x'] = 1
        session.save()
        before = session.session_key
        self.post_json(self.url, {'username': 'tester', 'password': 'pw'})
        self.assertNotEqual(self.client.session.session_key, before)

    def test_bad_credentials(self):
        for body in (
            {'username': 'tester', 'password': 'wrong'},
            {'username': 'nobody', 'password': 'pw'},
        ):
            with self.subTest(body=body):
                response = self.post_json(self.url, body)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn('testapp_user_id', self.client.session)

    def test_invalid_bodies(self):
        for body in (
            {'username': 'tester'},
            {'username': 'tester', 'password': 123},
            {'username': None, 'password': 'pw'},
            '[]',
            'not json',
            b'\xff\xfe',
        ):
            with self.subTest(body=body):
                self.assertEqual(self.post_json(self.url, body).status_code, 400)

    def test_rejects_get(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class SessionTests(LoggedInTestCase):
    def test_session_for_deleted_user_is_rejected(self):
        self.user.delete()
        self.assertEqual(self.client.get(reverse('get_device_name')).status_code, 401)


# --------------------------------------------------------------------------- addUser

class AddUserTests(LoggedInTestCase):
    def setUp(self):
        self.url = reverse('add_user')
        self.valid = {
            'username': 'newuser', 'password': 'secret',
            'email': 'n@example.com', 'phone_number': '0912345678', 'address': 'Taipei',
        }

    def test_creates_user_with_hashed_password(self):
        response = self.post_json(self.url, self.valid)
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(id=response.json()['user_id'])
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.phone_number, '0912345678')
        self.assertNotEqual(user.password, 'secret')
        self.assertTrue(user.check_password('secret'))

    def test_new_user_can_log_in(self):
        self.post_json(self.url, self.valid)
        response = self.post_json(reverse('login'), {'username': 'newuser', 'password': 'secret'})
        self.assertEqual(response.status_code, 200)

    def test_duplicate_username(self):
        self.post_json(self.url, self.valid)
        response = self.post_json(self.url, self.valid)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(User.objects.filter(username='newuser').count(), 1)

    def test_max_lengths_are_accepted(self):
        data = {**self.valid, 'username': 'u' * 10, 'email': 'e' * 25,
                'phone_number': '1' * 15, 'address': 'a' * 25}
        self.assertEqual(self.post_json(self.url, data).status_code, 201)

    def test_invalid_fields(self):
        cases = [{k: v for k, v in self.valid.items() if k != 'email'}]  # missing
        for field in self.valid:
            cases.append({**self.valid, field: ''})
            cases.append({**self.valid, field: 123})
        cases += [
            {**self.valid, 'username': 'u' * 11},
            {**self.valid, 'email': 'e' * 26},
            {**self.valid, 'phone_number': '1' * 16},
            {**self.valid, 'address': 'a' * 26},
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(self.post_json(self.url, data).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_invalid_json(self):
        self.assertEqual(self.post_json(self.url, '{bad').status_code, 400)
        self.assertEqual(self.post_json(self.url, '"text"').status_code, 400)

    def test_rejects_get(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


# --------------------------------------------------------------------------- addMeterData

class AddMeterDataTests(LoggedInTestCase):
    def setUp(self):
        make_user()  # credentials are sent in the body; no session needed
        self.url = reverse('add_meter_data')
        self.valid = {
            'username': 'tester', 'password': 'pw',
            'Time': 1700000000000, 'DeviceName': 'Meter1',
            'rPhaseVoltage': 220.5, 'sPhaseVoltage': 221, 'tPhaseVoltage': 219.8,
            'rPhaseCurrent': 1.2, 'sPhaseCurrent': 1.3, 'tPhaseCurrent': 1.1,
            'Factor': 0.95, 'TotalkWh': 123.4,
        }

    def test_creates_record(self):
        response = self.post_json(self.url, self.valid)
        self.assertEqual(response.status_code, 201)
        record = MeterData.objects.get(id=response.json()['id'])
        self.assertEqual(record.Time, 1700000000000)
        self.assertEqual(record.DeviceName, 'Meter1')
        self.assertEqual(record.sPhaseVoltage, 221.0)  # int accepted for float fields
        self.assertAlmostEqual(record.TotalkWh, 123.4)

    def test_time_boundaries_are_accepted(self):
        for time in (0, MAX_BIGINT):
            with self.subTest(time=time):
                self.assertEqual(self.post_json(self.url, {**self.valid, 'Time': time}).status_code, 201)

    def test_bad_credentials(self):
        for creds in ({'password': 'wrong'}, {'username': 'nobody'}):
            with self.subTest(creds=creds):
                self.assertEqual(self.post_json(self.url, {**self.valid, **creds}).status_code, 401)
        self.assertFalse(MeterData.objects.exists())

    def test_missing_credentials(self):
        data = {k: v for k, v in self.valid.items() if k != 'password'}
        self.assertEqual(self.post_json(self.url, data).status_code, 400)

    def test_invalid_fields(self):
        cases = []
        for field in self.valid:
            if field not in ('username', 'password'):
                cases.append({k: v for k, v in self.valid.items() if k != field})  # missing
        cases += [
            {**self.valid, 'Time': True},
            {**self.valid, 'Time': 1.5},
            {**self.valid, 'Time': '1700000000000'},
            {**self.valid, 'Time': -1},
            {**self.valid, 'Time': MAX_BIGINT + 1},  # used to crash with a 500
            {**self.valid, 'DeviceName': ''},
            {**self.valid, 'DeviceName': 5},
            {**self.valid, 'DeviceName': 'd' * 26},
            {**self.valid, 'Factor': True},
            {**self.valid, 'Factor': '0.9'},
            {**self.valid, 'Factor': None},
        ]
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(self.post_json(self.url, data).status_code, 400)
        self.assertFalse(MeterData.objects.exists())

    def test_non_finite_numbers(self):
        # Python's json module accepts these non-standard literals.
        for literal in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(literal=literal):
                body = json.dumps(self.valid).replace('123.4', literal)
                self.assertEqual(self.post_json(self.url, body).status_code, 400)
        self.assertFalse(MeterData.objects.exists())

    def test_rejects_get(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


# --------------------------------------------------------------------------- getMeterData

class GetMeterDataTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_meter_data')

        for t in (1000, 2000, 3000):
            make_record('A', t)
        for t in (1500, 2500):
            make_record('B', t)

    def get(self, **params):
        return self.client.get(self.url, params)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.get().status_code, 401)

    def test_rejects_post(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_default_returns_all_newest_first(self):
        body = self.get().json()
        self.assertEqual(body['total'], 5)
        self.assertEqual(body['page'], 1)
        self.assertEqual(body['pageSize'], 100)
        self.assertEqual(body['totalPages'], 1)
        self.assertEqual([r['Time'] for r in body['data']], [3.0, 2.5, 2.0, 1.5, 1.0])

    def test_empty_table(self):
        MeterData.objects.all().delete()
        body = self.get().json()
        self.assertEqual((body['data'], body['total'], body['totalPages']), ([], 0, 1))

    def test_filter_by_device_and_time(self):
        body = self.get(DeviceName='A', startTime=1500, endTime=3000).json()
        self.assertEqual([r['Time'] for r in body['data']], [3.0, 2.0])
        self.assertTrue(all(r['DeviceName'] == 'A' for r in body['data']))

    def test_unknown_device_returns_nothing(self):
        self.assertEqual(self.get(DeviceName='Z').json()['total'], 0)

    def test_paging(self):
        page1 = self.get(pageSize=2, page=1).json()
        page3 = self.get(pageSize=2, page=3).json()
        self.assertEqual(page1['totalPages'], 3)
        self.assertEqual([r['Time'] for r in page1['data']], [3.0, 2.5])
        self.assertEqual([r['Time'] for r in page3['data']], [1.0])
        self.assertEqual(self.get(pageSize=2, page=9).json()['data'], [])

    def test_huge_page_is_empty_not_an_error(self):
        response = self.get(page=10 ** 18)  # used to crash with a 500
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], [])

    def test_latest_per_device(self):
        body = self.get(latest=1).json()
        self.assertEqual(
            [(r['DeviceName'], r['Time']) for r in body['data']],
            [('A', 3.0), ('B', 2.5)],
        )

    def test_latest_accepts_true_and_false(self):
        self.assertEqual(self.get(latest='true').json()['total'], 2)
        self.assertEqual(self.get(latest='false').json()['total'], 5)
        self.assertEqual(self.get(latest=0).json()['total'], 5)

    def test_latest_respects_time_filter(self):
        body = self.get(latest=1, endTime=2000).json()
        self.assertEqual(
            [(r['DeviceName'], r['Time']) for r in body['data']],
            [('A', 2.0), ('B', 1.5)],
        )

    def test_live_value_page_request(self):
        """Mirror exactly what liveValue.html sends and relies on."""
        page = self.client.get(reverse('live_value')).content.decode()
        self.assertIn("data: { latest: 1, pageSize: 500 }", page)

        # Same-Time tie on device A: the higher id must win, as the old JS did.
        tie = make_record('A', 3000, kwh=9.0)
        body = self.get(latest=1, pageSize=500).json()
        self.assertEqual(body['total'], 2)
        self.assertEqual(body['totalPages'], 1)
        by_device = {r['DeviceName']: r for r in body['data']}
        self.assertEqual(by_device['A']['id'], tie.id)
        self.assertEqual(by_device['A']['TotalkWh'], 9.0)
        self.assertEqual(by_device['B']['Time'], 2.5)  # seconds, as the JS multiplies by 1000
        for record in body['data']:
            for field in ('rPhaseVoltage', 'sPhaseVoltage', 'tPhaseVoltage', 'rPhaseCurrent',
                          'sPhaseCurrent', 'tPhaseCurrent', 'Factor', 'TotalkWh'):
                self.assertIn(field, record)

    def test_invalid_params(self):
        for params in (
            {'page': 0}, {'page': 'x'}, {'pageSize': 0}, {'pageSize': 501},
            {'startTime': 'abc'}, {'startTime': -1}, {'endTime': '1.5'},
            {'startTime': 3000, 'endTime': 1000},
            {'DeviceName': 'x' * 26}, {'latest': 'maybe'},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)


# --------------------------------------------------------------------------- getTotalkWh

class GetTotalkWhTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_total_kwh')

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_empty_table(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'Time': None, 'TotalkWh': None})

    def test_sums_newest_reading_per_device(self):
        make_record('A', 1000, kwh=10)
        make_record('A', 3000, kwh=12)
        make_record('B', 2000, kwh=5)
        make_record('B', 1500, kwh=4)
        data = self.client.get(self.url).json()
        self.assertEqual(data['TotalkWh'], 17)
        self.assertEqual(data['Time'], 3.0)

    def test_tie_on_time_uses_highest_id(self):
        make_record('A', 1000, kwh=10)
        make_record('A', 1000, kwh=11)
        self.assertEqual(self.client.get(self.url).json()['TotalkWh'], 11)

    def test_matches_get_meter_data_latest(self):
        make_record('A', 1000, kwh=10)
        make_record('A', 3000, kwh=12)
        make_record('B', 2000, kwh=5)
        latest = self.client.get(reverse('get_meter_data'), {'latest': 1}).json()['data']
        total = self.client.get(self.url).json()['TotalkWh']
        self.assertEqual(total, sum(r['TotalkWh'] for r in latest))

    def test_rejects_post(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)


# --------------------------------------------------------------------------- getKWhRangeData

class GetKWhRangeDataTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_kwh_range_data')
        for t, kwh in ((3000, 13), (1000, 11), (2000, 12), (4000, 14)):
            make_record('A', t, kwh=kwh)
        make_record('B', 2000, kwh=99)

    def get(self, **params):
        return self.client.get(self.url, params)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.get(DeviceName='A', startTime=0, endTime=1).status_code, 401)

    def test_rejects_post(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_inclusive_range_oldest_first_in_milliseconds(self):
        body = self.get(DeviceName='A', startTime=1000, endTime=3000).json()
        self.assertEqual(body['data'], [
            {'DeviceName': 'A', 'Time': 1000, 'TotalkWh': 11.0},
            {'DeviceName': 'A', 'Time': 2000, 'TotalkWh': 12.0},
            {'DeviceName': 'A', 'Time': 3000, 'TotalkWh': 13.0},
        ])

    def test_single_instant_range(self):
        body = self.get(DeviceName='B', startTime=2000, endTime=2000).json()
        self.assertEqual([r['TotalkWh'] for r in body['data']], [99.0])

    def test_no_matches(self):
        self.assertEqual(self.get(DeviceName='Z', startTime=0, endTime=9999).json(), {'data': []})
        self.assertEqual(self.get(DeviceName='A', startTime=5000, endTime=9999).json(), {'data': []})

    def test_invalid_params(self):
        valid = {'DeviceName': 'A', 'startTime': 0, 'endTime': 1}
        for params in (
            {**valid, 'DeviceName': ''},
            {**valid, 'DeviceName': 'x' * 26},
            {k: v for k, v in valid.items() if k != 'DeviceName'},
            {k: v for k, v in valid.items() if k != 'startTime'},
            {k: v for k, v in valid.items() if k != 'endTime'},
            {**valid, 'startTime': 'abc'},
            {**valid, 'endTime': '1.5'},
            {**valid, 'startTime': -1},
            {**valid, 'startTime': 5, 'endTime': 1},
        ):
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)


# --------------------------------------------------------------------------- getDeviceName

class GetDeviceNameTests(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('get_device_name')

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_rejects_post(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_empty(self):
        self.assertEqual(self.client.get(self.url).json(), {'data': []})

    def test_distinct_and_sorted(self):
        for device, t in (('C', 1), ('A', 2), ('B', 3), ('A', 4), ('C', 5)):
            make_record(device, t)
        self.assertEqual(self.client.get(self.url).json(), {'data': ['A', 'B', 'C']})
