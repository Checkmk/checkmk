import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    (
        (None, {
            'onredirect': 'follow',
            'port': 80,
            'uri': '/images',
            'urlize': True,
            'virthost': ('www.test123.de', True)
        }),
        [
            '-I', 'www.test123.de', '-H', 'www.test123.de', '-p', 80, '-u', '/images',
            '--onredirect=follow', '-L'
        ],
    ),
    (
        (None, {
            'extended_perfdata': True,
            'method': 'CONNECT',
            'port': 3128,
            'proxy': '163.172.86.64',
            'ssl': 'auto',
            'uri': '/images',
            'virthost': ('www.test123.de', True)
        }),
        [
            '-I', '163.172.86.64', '-H', 'www.test123.de', '-p', 3128, '-u', '/images', '--ssl',
            '--extended-perfdata', '-j', 'CONNECT'
        ],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
        }),
        ['-C', '10,20', '-p', '42', 'www.test123.com'],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': 'p.roxy',
        }),
        ['-C', '10,20', '--ssl', '-j', 'CONNECT', 'p.roxy', 'www.test123.com:42'],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': 'p.roxy:23',
        }),
        ['-C', '10,20', '-p', '23', '--ssl', '-j', 'CONNECT', 'p.roxy', 'www.test123.com:42'],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': '[dead:beef::face]:23',
        }),
        [
            '-C', '10,20', '-p', '23', '--ssl', '-j', 'CONNECT', '[dead:beef::face]',
            'www.test123.com:42'
        ],
    ),
    (
        (None, {
            'virthost': ("virtual.host", True),
            'proxy': "foo.bar",
        }),
        ['-I', 'foo.bar', '-H', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", False),
            'proxy': "foo.bar",
        }),
        ['-I', 'foo.bar', '-H', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", True),
        }),
        ['-I', 'virtual.host', '-H', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", False),
        }),
        ['-I', '$_HOSTADDRESS_4$', '-H', 'virtual.host'],
    ),
])
def test_check_http_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check('check_http')
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize('params,expected_description', [
    (
        (u'No SSL Test', {}),
        u'HTTP No SSL Test',
    ),
    (
        (u'Test with SSL', {
            'ssl': "auto"
        }),
        u'HTTPS Test with SSL',
    ),
    (
        (u'^No Prefix Test', {}),
        u'No Prefix Test',
    ),
])
def test_check_http_service_description(check_manager, params, expected_description):
    active_check = check_manager.get_active_check('check_http')
    assert active_check.run_service_description(params) == expected_description
