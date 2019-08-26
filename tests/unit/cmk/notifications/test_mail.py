# -*- coding: utf-8 -*-

import pytest  # type: ignore

import cmk.notification_plugins.mail as mail


@pytest.mark.parametrize("notification_type, expected", [
    ("PROBLEM", (
        "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
        '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; <span class="state$@STATE$">$@STATE$</span>',
    )),
    ("RECOVERY", (
        "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
        '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; <span class="state$@STATE$">$@STATE$</span>',
    )),
    ("FLAPPINGSTART", (
        "Started Flapping",
        "Started Flapping",
    )),
    ("FLAPPINGSTOP", (
        'Stopped Flapping ($@SHORTSTATE$)',
        'Stopped Flapping (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ("DOWNTIMESTART", (
        "Downtime Start ($@SHORTSTATE$)",
        'Downtime Start (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ("DOWNTIMEEND", (
        "Downtime End ($@SHORTSTATE$)",
        'Downtime End (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ("DOWNTIMECANCELLED", (
        "Downtime Cancelled ($@SHORTSTATE$)",
        'Downtime Cancelled (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ("ACKNOWLEDGEMENT", (
        "Acknowledged ($@SHORTSTATE$)",
        'Acknowledged (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ("CUSTOM", (
        "Custom Notification ($@SHORTSTATE$)",
        'Custom Notification (while <span class="state$@STATE$">$@STATE$</span>)',
    )),
    ('UNKNOWN', (
        "UNKNOWN",
        "UNKNOWN",
    )),
])
def test_event_templates(notification_type, expected):
    assert mail.event_templates(notification_type) == expected


HOSTNAME_ELEMENT = (
    "hostname",
    "both",
    True,
    "all",
    "Host",
    "$HOSTNAME$ ($HOSTALIAS$)",
    "$LINKEDHOSTNAME$ ($HOSTALIAS$)",
)
SERVICEDESC_ELEMENT = (
    "servicedesc",
    "service",
    True,
    "all",
    "Service",
    "$SERVICEDESC$",
    "$LINKEDSERVICEDESC$",
)

ALERTHANDLER_NAME_ELEMENT = (
    "alerthandler_name",
    "both",
    True,
    "alerthandler",
    "Name of alert handler",
    "$ALERTHANDLERNAME$",
    "$ALERTHANDLERNAME$",
)


@pytest.mark.parametrize(
    "args, expected",
    [
        (  # Show the hostname column in host notifications
            ("host", False, ['hostname'], [HOSTNAME_ELEMENT]),
            (
                'Host:                $HOSTNAME$ ($HOSTALIAS$)\n',
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr>',
            ),
        ),
        (  # Show the hostname column in service notifications
            ("service", False, ['hostname'], [HOSTNAME_ELEMENT]),
            (
                'Host:                $HOSTNAME$ ($HOSTALIAS$)\n',
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr>',
            ),
        ),
        (  # Don't show the servicedesc column in host notifications
            ("host", False, ['servicedesc'], [SERVICEDESC_ELEMENT]),
            ('', ''),
        ),
        (  # Show the servicedesc column in service notifications
            ("service", False, ['servicedesc'], [SERVICEDESC_ELEMENT]),
            (
                'Service:             $SERVICEDESC$\n',
                '<tr class="even0"><td class=left>Service</td><td>$LINKEDSERVICEDESC$</td></tr>',
            ),
        ),
        (  # Columns are concatenated, the order is determined by the body elements
            (
                "service",
                False,
                ['servicedesc', 'hostname'],
                [HOSTNAME_ELEMENT, SERVICEDESC_ELEMENT],
            ),
            (
                'Host:                $HOSTNAME$ ($HOSTALIAS$)\nService:             $SERVICEDESC$\n',
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr><tr class="odd0"><td class=left>Service</td><td>$LINKEDSERVICEDESC$</td></tr>',
            ),
        ),
        (  # Don't show the alerthandler_name if is_alert_handler is False
            ("service", False, ['alerthandler_name'], [ALERTHANDLER_NAME_ELEMENT]),
            ('', ''),
        ),
        (  # Show the alerthandler_name if is_alert_handler is True
            ("service", True, ['alerthandler_name'], [ALERTHANDLER_NAME_ELEMENT]),
            (
                'Name of alert handler: $ALERTHANDLERNAME$\n',
                '<tr class="even0"><td class=left>Name of alert handler</td><td>$ALERTHANDLERNAME$</td></tr>',
            ),
        ),
    ])
def test_body_templates(args, expected):
    assert mail.body_templates(*args) == expected


def mock_service_context():
    return {
        'CONTACTALIAS': u'cmkadmin',
        'CONTACTEMAIL': u'test@abc.de',
        'CONTACTNAME': u'cmkadmin',
        'CONTACTPAGER': u'',
        'CONTACTS': u'cmkadmin',
        'DATE': u'2019-03-20',
        'HOSTACKAUTHOR': u'',
        'HOSTACKCOMMENT': u'',
        'HOSTADDRESS': u'127.0.0.1',
        'HOSTALIAS': u'heute',
        'HOSTATTEMPT': u'1',
        'HOSTCHECKCOMMAND': u'check-mk-host-smart',
        'HOSTCONTACTGROUPNAMES': u'all',
        'HOSTDOWNTIME': u'0',
        'HOSTFORURL': u'heute',
        'HOSTGROUPNAMES': u'check_mk',
        'HOSTNAME': u'heute',
        'HOSTNOTES': u'',
        'HOSTNOTESURL': u'',
        'HOSTNOTIFICATIONNUMBER': u'1',
        'HOSTOUTPUT': u'<script>console.log("evil");</script>Packet received via smart PING (!)',
        'HOSTPERFDATA': u'',
        'HOSTPROBLEMID': u'0',
        'HOSTSHORTSTATE': u'UP',
        'HOSTSTATE': u'UP',
        'HOSTSTATEID': u'0',
        'HOSTTAGS': u'/wato/ cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp wato',
        'HOSTURL': u'/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute',
        'HOST_ADDRESS_4': u'127.0.0.1',
        'HOST_ADDRESS_6': u'',
        'HOST_ADDRESS_FAMILY': u'4',
        'HOST_EC_CONTACT': u'',
        'HOST_FILENAME': u'/wato/hosts.mk',
        'HOST_SL': u'',
        'HOST_TAGS': u'/wato/ cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp wato',
        'LASTHOSTPROBLEMID': u'0',
        'LASTHOSTSHORTSTATE': u'UP',
        'LASTHOSTSTATE': u'UP',
        'LASTHOSTSTATECHANGE': u'1552482625',
        'LASTHOSTSTATECHANGE_REL': u'7d 02:41:21',
        'LASTHOSTSTATEID': u'0',
        'LASTHOSTUP': u'1553097106',
        'LASTHOSTUP_REL': u'0d 00:00:00',
        'LASTSERVICEOK': u'1553097092',
        'LASTSERVICEOK_REL': u'0d 00:00:14',
        'LASTSERVICEPROBLEMID': u'171',
        'LASTSERVICESHORTSTATE': u'OK',
        'LASTSERVICESTATE': u'OK',
        'LASTSERVICESTATECHANGE': u'1553097106',
        'LASTSERVICESTATECHANGE_REL': u'0d 00:00:00',
        'LASTSERVICESTATEID': u'0',
        'LOGDIR': u'/omd/sites/heute/var/check_mk/notify',
        'LONGDATETIME': u'Wed Mar 20 16:51:46 CET 2019',
        'LONGHOSTOUTPUT': u'',
        'LONGSERVICEOUTPUT': u'<script>console.log("evil");</script>(!)\nanother line\\nlast line',
        'MAIL_COMMAND': u"mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
        'MAXHOSTATTEMPTS': u'1',
        'MAXSERVICEATTEMPTS': u'1',
        'MICROTIME': u'1553097106779348',
        'MONITORING_HOST': u'Klappschloss',
        'NOTIFICATIONAUTHOR': u'',
        'NOTIFICATIONAUTHORALIAS': u'',
        'NOTIFICATIONAUTHORNAME': u'',
        'NOTIFICATIONCOMMENT': u'',
        'NOTIFICATIONTYPE': u'PROBLEM',
        'OMD_ROOT': u'/omd/sites/heute',
        'OMD_SITE': u'heute',
        'PARAMETER_INSERT_HTML_SECTION': u'<h1>This is important</h1>\n',
        'PREVIOUSHOSTHARDSHORTSTATE': u'UP',
        'PREVIOUSHOSTHARDSTATE': u'UP',
        'PREVIOUSHOSTHARDSTATEID': u'0',
        'PREVIOUSSERVICEHARDSHORTSTATE': u'OK',
        'PREVIOUSSERVICEHARDSTATE': u'OK',
        'PREVIOUSSERVICEHARDSTATEID': u'0',
        'SERVICEACKAUTHOR': u'',
        'SERVICEACKCOMMENT': u'',
        'SERVICEATTEMPT': u'1',
        'SERVICECHECKCOMMAND': u'check_mk-kernel.util',
        'SERVICECONTACTGROUPNAMES': u'all',
        'SERVICEDESC': u'CPU utilization',
        'SERVICEDISPLAYNAME': u'CPU utilization',
        'SERVICEDOWNTIME': u'0',
        'SERVICEFORURL': u'CPU%20utilization',
        'SERVICEGROUPNAMES': u'',
        'SERVICENOTES': u'',
        'SERVICENOTESURL': u'',
        'SERVICENOTIFICATIONNUMBER': u'1',
        'SERVICEOUTPUT': u'<script>console.log("evil");</script> Ok (!)',
        'SERVICEPERFDATA': u'',
        'SERVICEPROBLEMID': u'171',
        'SERVICESHORTSTATE': u'WARN',
        'SERVICESTATE': u'WARNING',
        'SERVICESTATEID': u'1',
        'SERVICEURL': u'/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20utilization%26site%3Dheute',
        'SERVICE_EC_CONTACT': u'',
        'SERVICE_SL': u'',
        'SHORTDATETIME': u'2019-03-20 16:51:46',
        'SUBJECT': u'Check_MK: heute/CPU utilization OK -> WARN',
        'SVC_SL': u'',
        'WHAT': u'SERVICE',
        'PARAMETER_FROM': u'check_mk@myinstance.com',
        'PARAMETER_REPLY_TO': u'reply@myinstance.com',
        'PARAMETER_URL_PREFIX_AUTOMATIC': u'http',
    }


SERVICE_CONTENT_TXT = """\
Host:                heute (heute)
Service:             CPU utilization
Event:               OK -> WARN
Address:             127.0.0.1
Date / Time:         Wed Mar 20 16:51:46 CET 2019
Plugin Output:       &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)
Additional Output:   &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)
another line\\nlast line
Host Metrics:        \n\
Service Metrics:     \n\
"""


# TODO: validate the HTML content
def test_mail_content_from_service_context(mocker):
    mocker.patch("cmk.notification_plugins.mail.render_pnp_graphs", lambda context: [])

    # The items below are added by the mail plugin
    context = mock_service_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    content = mail.SingleEmailContent(mock_service_context)

    # The state markers (!) and (!!) as well as the states in EVENT_TXT have to be
    # replaced with HTML, but raw input from plugins has to be escaped.
    # LONGSERVICEOUTPUT_HTML additionally replaces '\n' and '\\n' by '<br>'.
    assert content.context["EVENT_TXT"] == "OK -> WARN"
    assert content.context[
        "EVENT_HTML"] == '<span class="stateOK">OK</span> &rarr; <span class="stateWARNING">WARNING</span>'
    assert content.context[
        "HOSTOUTPUT"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;Packet received via smart PING (!)'
    assert content.context[
        "HOSTOUTPUT_HTML"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;Packet received via smart PING <b class="stmarkWARNING">WARN</b>'
    assert content.context[
        "SERVICEOUTPUT"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)'
    assert content.context[
        "SERVICEOUTPUT_HTML"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok <b class="stmarkWARNING">WARN</b>'
    assert content.context[
        "LONGSERVICEOUTPUT"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)\nanother line\\nlast line'
    assert content.context[
        "LONGSERVICEOUTPUT_HTML"] == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;<b class="stmarkWARNING">WARN</b><br>another line<br>last line'

    assert content.context[
        'LINKEDHOSTNAME'] == '<a href="http://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute">heute</a>'
    assert content.context[
        'LINKEDSERVICEDESC'] == '<a href="http://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20utilization%26site%3Dheute">CPU utilization</a>'

    assert content.mailto == 'test@abc.de'
    assert content.subject == 'Check_MK: heute/CPU utilization OK -> WARN'
    assert content.from_address == u'check_mk@myinstance.com'
    assert content.reply_to == u'reply@myinstance.com'
    assert content.content_txt == SERVICE_CONTENT_TXT
    assert content.attachments == []


def mock_host_context():
    return {
        'CONTACTALIAS': u'cmkadmin',
        'CONTACTEMAIL': u'test@abc.de',
        'CONTACTNAME': u'cmkadmin',
        'CONTACTPAGER': u'',
        'CONTACTS': u'cmkadmin',
        'DATE': u'2019-08-23',
        'HOSTACKAUTHOR': u'',
        'HOSTACKCOMMENT': u'',
        'HOSTADDRESS': u'127.0.0.1',
        'HOSTALIAS': u'heute',
        'HOSTATTEMPT': u'1',
        'HOSTCHECKCOMMAND': u'check-mk-host-smart',
        'HOSTCONTACTGROUPNAMES': u'all',
        'HOSTDOWNTIME': u'0',
        'HOSTFORURL': u'heute',
        'HOSTGROUPNAMES': u'check_mk',
        'HOSTNAME': u'heute',
        'HOSTNOTES': u'',
        'HOSTNOTESURL': u'',
        'HOSTNOTIFICATIONNUMBER': u'1',
        'HOSTOUTPUT': u'Packet received via smart PING',
        'HOSTPERFDATA': u'',
        'HOSTPROBLEMID': u'10',
        'HOSTSHORTSTATE': u'UP',
        'HOSTSTATE': u'UP',
        'HOSTSTATEID': u'0',
        'HOSTTAGS': u'/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
        'HOSTURL': u'/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute',
        'HOST_ADDRESS_4': u'127.0.0.1',
        'HOST_ADDRESS_6': u'',
        'HOST_ADDRESS_FAMILY': u'4',
        'HOST_EC_CONTACT': u'',
        'HOST_FILENAME': u'/wato/hosts.mk',
        'HOST_SL': u'',
        'HOST_TAGS': u'/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp',
        'LASTHOSTPROBLEMID': u'10',
        'LASTHOSTSHORTSTATE': u'DOWN',
        'LASTHOSTSTATE': u'DOWN',
        'LASTHOSTSTATECHANGE': u'1566551597',
        'LASTHOSTSTATECHANGE_REL': u'0d 00:00:00',
        'LASTHOSTSTATEID': u'1',
        'LASTHOSTUP': u'1566551597',
        'LASTHOSTUP_REL': u'0d 00:00:00',
        'LOGDIR': u'/omd/sites/heute/var/check_mk/notify',
        'LONGDATETIME': u'Fri Aug 23 11:13:17 CEST 2019',
        'LONGHOSTOUTPUT': u'',
        'MAIL_COMMAND': u"mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
        'MAXHOSTATTEMPTS': u'1',
        'MICROTIME': u'1566551597286646',
        'MONITORING_HOST': u'Klappschloss',
        'NOTIFICATIONAUTHOR': u'',
        'NOTIFICATIONAUTHORALIAS': u'',
        'NOTIFICATIONAUTHORNAME': u'',
        'NOTIFICATIONCOMMENT': u'',
        'NOTIFICATIONTYPE': u'RECOVERY',
        'OMD_ROOT': u'/omd/sites/heute',
        'OMD_SITE': u'heute',
        'PARAMETER_URL_PREFIX_AUTOMATIC': u'https',
        'PREVIOUSHOSTHARDSHORTSTATE': u'DOWN',
        'PREVIOUSHOSTHARDSTATE': u'DOWN',
        'PREVIOUSHOSTHARDSTATEID': u'1',
        'SHORTDATETIME': u'2019-08-23 11:13:17',
        'WHAT': u'HOST',
    }


HOST_CONTENT_TXT = """\
Host:                heute (heute)
Event:               DOWN -> UP
Address:             127.0.0.1
Date / Time:         Fri Aug 23 11:13:17 CEST 2019
Plugin Output:       Packet received via smart PING
Metrics:             \n\
"""


def test_mail_content_from_host_context(mocker):
    mocker.patch("cmk.notification_plugins.mail.render_pnp_graphs", lambda context: [])
    mocker.patch("cmk.notification_plugins.mail.socket.getfqdn", lambda: 'mysite.com')

    context = mock_host_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    content = mail.SingleEmailContent(mock_host_context)

    assert content.context["EVENT_TXT"] == "DOWN -> UP"
    assert content.context[
        "EVENT_HTML"] == '<span class="stateDOWN">DOWN</span> &rarr; <span class="stateUP">UP</span>'
    assert content.context["HOSTOUTPUT"] == 'Packet received via smart PING'
    assert content.context["HOSTOUTPUT_HTML"] == 'Packet received via smart PING'
    assert "SERVICEOUTPUT" not in content.context
    assert "SERVICEOUTPUT_HTML" not in content.context
    assert "LONGSERVICEOUTPUT" not in content.context
    assert "LONGSERVICEOUTPUT_HTML" not in content.context

    assert content.context[
        'LINKEDHOSTNAME'] == '<a href="https://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute">heute</a>'
    assert content.context['LINKEDSERVICEDESC'] == ''

    assert content.mailto == 'test@abc.de'
    assert content.subject == 'Check_MK: heute - DOWN -> UP'
    assert content.from_address == u'checkmk@mysite.com'
    assert content.reply_to is None
    assert content.content_txt == HOST_CONTENT_TXT
    assert content.attachments == []
