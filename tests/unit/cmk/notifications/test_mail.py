# -*- coding: utf-8 -*-

import pytest
from cmk.notification_plugins.mail import SingleEmailContent


def mock_context():
    return {
        'CONTACTALIAS': u'cmkadmin',
        'CONTACTEMAIL': u'test@abc.de',
        'CONTACTNAME': u'cmkadmin',
        'CONTACTPAGER': u'',
        'CONTACTS': u'cmkadmin',
        'DATE': u'2019-03-20',
        'EVENT_HTML': u'<span class="stateOK">OK</span> &rarr; <span class="stateWARNING">WARNING</span>',
        'EVENT_TXT': u'OK -> WARN',
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
        'HOSTOUTPUT_HTML': u'Packet received via smart PING',
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
        'LONGSERVICEOUTPUT': u'',
        'LONGSERVICEOUTPUT_HTML': u'',
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
        'SERVICEOUTPUT': u'Manually set to Warning by cmkadmin',
        'SERVICEOUTPUT_HTML': u'Manually set to Warning by cmkadmin',
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
Plugin Output:       Manually set to Warning by cmkadmin
Additional Output:   \n\
Host Metrics:        \n\
Service Metrics:     \n\
"""


# TODO: validate the HTML content
def test_mail_content_from_context(mocker):
    mocker.patch("cmk.notification_plugins.mail.render_pnp_graphs", lambda context: [])

    c = mocker.patch("cmk.notification_plugins.utils.html_escape_context")
    content = SingleEmailContent(mock_context)
    c.assert_called_once()

    assert content.mailto == 'test@abc.de'
    assert content.subject == 'Check_MK: heute/CPU utilization OK -> WARN'
    assert content.from_address == u'check_mk@myinstance.com'
    assert content.reply_to == u'reply@myinstance.com'
    assert content.content_txt == CONTENT_TXT
    assert content.attachments == []
