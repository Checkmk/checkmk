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
            '-u',
            '/images',
            '--onredirect=follow',
            '-L',
            '-H',
            'www.test123.de',
            '--sni',
            '-p',
            '80',
            'www.test123.de',
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
            '-u',
            '/images',
            '--ssl',
            '--extended-perfdata',
            '-j',
            'CONNECT',
            '-H',
            'www.test123.de',
            '--sni',
            '163.172.86.64',
            'www.test123.de:3128',
        ],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
        }),
        ['-C', '10,20', '-H', 'www.test123.com', '--sni', '-p', '42', 'www.test123.com'],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': 'p.roxy',
        }),
        [
            '-C', '10,20', '--ssl', '-j', 'CONNECT', '-H', 'www.test123.com', '--sni', 'p.roxy',
            'www.test123.com:42'
        ],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': 'p.roxy:23',
        }),
        [
            '-C', '10,20', '--ssl', '-j', 'CONNECT', '-H', 'www.test123.com', '--sni', '-p', '23',
            'p.roxy', 'www.test123.com:42'
        ],
    ),
    (
        (None, {
            'cert_days': (10, 20),
            'cert_host': 'www.test123.com',
            'port': '42',
            'proxy': '[dead:beef::face]:23',
        }),
        [
            '-C', '10,20', '--ssl', '-j', 'CONNECT', '-H', 'www.test123.com', '--sni', '-p', '23',
            '[dead:beef::face]', 'www.test123.com:42'
        ],
    ),
    (
        {
            'host': {
                "address": 'www.test123.com',
                "port": 42,
                "address_family": 'ipv6'
            },
            'proxy': {
                "address": '[dead:beef::face]',
                "port": 23
            },
            'mode': ('cert', {
                'cert_days': (10, 20)
            }),
            'disable_sni': True
        },
        [
            '-C', '10,20', '--ssl', '-j', 'CONNECT', '-H', 'www.test123.com', '-6', '-p', '23',
            '[dead:beef::face]', 'www.test123.com:42'
        ],
    ),
    (
        (None, {
            'virthost': ("virtual.host", True),
            'proxy': "foo.bar",
        }),
        ['-H', 'virtual.host', '--sni', 'foo.bar', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", False),
            'proxy': "foo.bar",
        }),
        ['-H', 'virtual.host', '--sni', 'foo.bar', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", True),
        }),
        ['-H', 'virtual.host', '--sni', 'virtual.host'],
    ),
    (
        (None, {
            'virthost': ("virtual.host", False),
        }),
        ['-H', 'virtual.host', '--sni', '$_HOSTADDRESS_4$'],
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
