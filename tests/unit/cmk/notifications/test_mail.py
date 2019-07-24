# -*- coding: utf-8 -*-

from cmk.notification_plugins.mail import SingleEmailContent


def mock_context():
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
        'LINKEDHOSTNAME': u'heute',
        'LINKEDSERVICEDESC': u'CPU utilization',
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
        'PARAMETER_REPLY_TO': u'reply@myinstance.com'
    }


CONTENT_TXT = """\
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
def test_mail_content_from_context(mocker):
    mocker.patch("cmk.notification_plugins.mail.render_pnp_graphs", lambda context: [])

    # The items below are added by the mail plugin
    context = mock_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context

    content = SingleEmailContent(mock_context)

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

    assert content.mailto == 'test@abc.de'
    assert content.subject == 'Check_MK: heute/CPU utilization OK -> WARN'
    assert content.from_address == u'check_mk@myinstance.com'
    assert content.reply_to == u'reply@myinstance.com'
    assert content.content_txt == CONTENT_TXT
    assert content.attachments == []
