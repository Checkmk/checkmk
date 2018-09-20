import pytest
from cmk.notification_plugins import utils


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
    utils.extend_context_with_link_urls(context, link_template)
    assert context[testkey] == result


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
