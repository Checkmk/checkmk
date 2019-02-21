import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'params,expected_args',
    [(
        (None, {
            'onredirect': 'follow',
            'port': 80,
            'uri': '/images',
            'urlize': True,
            'virthost': ('www.test123.de', True)
        }),
        ['-H', 'www.test123.de', '-p', 80, '-u', '/images', '--onredirect=follow', '-L'],
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
             'cert_host': 'www.test123.com'
         }),
         ['-I', 'www.test123.com', '-H', '$_HOSTADDRESS_4$', '-C', '10,20'],
     )])
def test_check_http_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present. The tests do not check the order of arguments."""
    active_check = check_manager.get_active_check('check_http')
    assert sorted(active_check.run_argument_function(params)) == sorted(expected_args)


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
