import pytest
from cmk.notification_plugins.utils import extend_context_with_link_urls


@pytest.mark.parametrize("context, link_template, testkey, result", [
    ({
        "PARAMETER_URL_PREFIX": "https://host/site/check_mk",
        "HOSTURL": "/view?key=val",
        "HOSTNAME": "site",
        "WHAT": 'HOST',
    }, "<%s|%s>", "LINKEDHOSTNAME", "<https://host/site/view?key=val|site>"),
    ({
        "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
        "MONITORING_HOST": "localhost",
        "OMD_SITE": "testsite",
        "HOSTURL": "/view?key=val",
        "SERVICEURL": "/view?key=val",
        "HOSTNAME": "site1",
        "SERVICEDESC": "first",
        "WHAT": 'SERVICE',
    }, '<a href="%s">%s</a>', "LINKEDSERVICEDESC",
     '<a href="http://localhost/testsite/view?key=val">first</a>'),
    ({
        "HOSTURL": "/view?key=val",
        "HOSTNAME": "site2",
        "WHAT": 'SERVICE',
    }, '<a href="%s">%s</a>', "LINKEDSERVICEDESC", ''),
])
def test_extend_with_link_urls(context, link_template, testkey, result):
    extend_context_with_link_urls(context, link_template)
    assert context[testkey] == result
