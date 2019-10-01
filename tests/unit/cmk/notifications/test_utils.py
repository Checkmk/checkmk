import pytest
from cmk.notification_plugins import utils


@pytest.mark.parametrize(
    "context, result",
    [
        (  # host context with url parameter
            {
                "PARAMETER_URL_PREFIX": "https://host/site/check_mk",
                "HOSTURL": "/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
                "WHAT": 'HOST',
            },
            "https://host/site/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "WHAT": 'SERVICE',
            },
            "https://localhost/testsite/view?key=val",
        ),
        (  # host context withour url parameter
            {
                "WHAT": 'HOST',
            },
            "",
        ),
        (  # service context without url parameter
            {
                "WHAT": 'SERVICE',
            },
            "",
        ),
    ])
def test_host_url_from_context(context, result):
    host_url = utils.host_url_from_context(context)
    assert host_url == result


@pytest.mark.parametrize(
    "context, result",
    [
        (  # host context with url parameter
            {
                "PARAMETER_URL_PREFIX": "https://host/site/check_mk",
                "WHAT": 'HOST',
            },
            "",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "SERVICEURL": '/check_mk/index.py?start_url=view.py?view_name=service&host=test&service=foos&site=heute',
                "WHAT": 'SERVICE',
            },
            "http://localhost/testsite/check_mk/index.py?start_url=view.py?view_name=service&host=test&service=foos&site=heute",
        ),
        (  # host context without url parameter
            {
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "site2",
                "WHAT": 'SERVICE',
            },
            "",
        ),
        (  # service context without url parameter
            {
                "WHAT": 'SERVICE',
            },
            "",
        ),
    ])
def test_service_url_from_context(context, result):
    service_url = utils.service_url_from_context(context)
    assert service_url == result


@pytest.mark.parametrize("template, url, text, expected_link", [
    (
        "<%s|%s>",
        "https://host/site/view?key=val",
        "site",
        "<https://host/site/view?key=val|site>",
    ),
    (
        '<a href="%s">%s</a>',
        'http://localhost/testsite/view?key=val',
        'first',
        '<a href="http://localhost/testsite/view?key=val">first</a>',
    ),
    (
        '<a href="%s">%s</a>',
        '',
        'host1',
        'host1',
    ),
])
def test_format_link(template, url, text, expected_link):
    actual_link = utils.format_link(template, url, text)
    assert actual_link == expected_link


@pytest.mark.parametrize("context, template, result", [
    ({
        "HOSTNAME": "localhost",
        "SERVICENOTESURL": "$HOSTNAME$ is on fire"
    }, """
$HOSTNAME$
$SERVICENOTESURL$
$UNKNOWN$
""", "\nlocalhost\nlocalhost is on fire\n\n"),
    ({
        "HOSTNAME": "localhost",
        "SERVICENOTESURL": "$HOSTNAME$"
    }, "\n$CONTEXT_ASCII$\n$CONTEXT_HTML$", """
HOSTNAME=localhost
SERVICENOTESURL=localhost

<table class=context>
<tr><td class=varname>HOSTNAME</td><td class=value>localhost</td></tr>
<tr><td class=varname>SERVICENOTESURL</td><td class=value>localhost</td></tr>
</table>\n"""),
])
def test_substitute_context(context, template, result):
    assert result == utils.substitute_context(template, context)


def test_read_bulk_contents(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', ('key=val', '\n', 'key2=val2', 'a comment'))
    assert utils.read_bulk_contexts() == ({'key': 'val'}, [{'key2': 'val2'}])
    assert capsys.readouterr().err == "Invalid line 'a comment' in bulked notification context\n"


@pytest.mark.parametrize("context, hosts, result", [
    ([{
        "k": "y"
    }], ["local", "host"], "Check_MK: 1 notifications for 2 hosts"),
    ([{
        "k": "y"
    }, {
        "l": "p"
    }], ["first"], "Check_MK: 2 notifications for first"),
    ([{
        "PARAMETER_BULK_SUBJECT": "Check_MK: $FOLDER$ gone $COUNT_HOSTS$ host",
        "HOSTTAGS": "/wato/lan cmk-agent ip-v4 prod site:heute tcp wato"
    }], ["first"], "Check_MK: lan gone 1 host"),
])
def test_get_bulk_notification_subject(context, hosts, result):
    assert utils.get_bulk_notification_subject(context, hosts) == result


@pytest.mark.parametrize("value, result", [
    ("http://local.host", "http://local.host"),
    ("webhook_url\thttp://webhook.host", "http://webhook.host"),
    ("store\tpwservice", "http://secret.host"),
])
def test_api_endpoint_url(monkeypatch, value, result):
    monkeypatch.setattr('cmk.utils.password_store.extract', lambda x: 'http://secret.host')
    assert utils.retrieve_from_passwordstore(value) == result


@pytest.mark.parametrize(
    "input_context,expected_context",
    [
        # If not explicitly allowed as unescaped...
        (
            {
                'PARAMETER_HOST_SUBJECT': '$HOSTALIAS$ > $HOSTSTATE$ < $HOST_SERVERTYP$',
                'PARAMETER_SERVICE_SUBJECT': '<>&',
                'PARAMETER_BULK_SUBJECT': '<>&',
                'PARAMETER_INSERT_HTML_SECTION': '<h1>Important</h1>',
                'PARAMETER_FROM': 'Harri Hirsch <harri.hirsch@test.de>',
                'PARAMETER_REPLY_TO': 'Harri Hirsch <harri.hirsch@test.de>',
            },
            {
                'PARAMETER_HOST_SUBJECT': '$HOSTALIAS$ > $HOSTSTATE$ < $HOST_SERVERTYP$',
                'PARAMETER_SERVICE_SUBJECT': '<>&',
                'PARAMETER_BULK_SUBJECT': '<>&',
                'PARAMETER_INSERT_HTML_SECTION': '<h1>Important</h1>',
                'PARAMETER_FROM': 'Harri Hirsch <harri.hirsch@test.de>',
                'PARAMETER_REPLY_TO': 'Harri Hirsch <harri.hirsch@test.de>',
            },
        ),
        # ... all variables will be escaped
        (
            {
                'SERVICEOUTPUT': '<h1>Important</h1>'
            },
            {
                'SERVICEOUTPUT': '&lt;h1&gt;Important&lt;/h1&gt;'
            },
        ),
    ])
def test_escape_context(input_context, expected_context):
    utils.html_escape_context(input_context)
    assert input_context == expected_context
