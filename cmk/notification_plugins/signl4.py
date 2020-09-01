#!/usr/bin/env python3
# SIGNL4 Alerting
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) 2020 Derdack GmbH
#          SIGNL4 <info@signl4.com>
# Reliable team alerting using SIGNL4.

import sys
import json
import requests


from cmk.notification_plugins import utils

api_url = "https://connect.signl4.com/webhook/"

def main():
    context = utils.collect_context()

    message = get_text(context)

    password = context["PARAMETER_PASSWORD"]

    return send_alert(password, message)

def get_text(context):

    host_name = context['HOSTNAME']
    notification_type = context['NOTIFICATIONTYPE']
    service_state = ''
    service_desc = ''
    service_output = ''
    host_state = ''
    notification_comment = ''
    contact_name = context['CONTACTNAME']
    contact_alias = context['CONTACTALIAS']
    contact_email = context['CONTACTEMAIL']
    contact_pager = context['CONTACTPAGER'].replace(' ', '')
    description = notification_type + ' on ' + host_name
    service_problem_id = ''
    
    host_problem_id = context['HOSTPROBLEMID']
    date_time = context['SHORTDATETIME']

    # Prepare Default information and Type PROBLEM, RECOVERY
    if context['WHAT'] == 'SERVICE':
        if notification_type in [ "PROBLEM", "RECOVERY" ]:
            service_state = context['SERVICESTATE']
            service_desc = context['SERVICEDESC']
            service_output = context['SERVICEOUTPUT']
            description += ' (' + service_desc + ')'
            service_problem_id = context['SERVICEPROBLEMID']
        else:
            service_desc = context['SERVICEDESC']
            description += ' (' + service_desc + ')'

    else:
        if notification_type in [ "PROBLEM", "RECOVERY" ]:
            host_state = context['HOSTSTATE']
            description += ' (' + host_state + ')'
        else:
            description += ' (' + host_state + ')'

    # Remove placeholder "$SERVICEPROBLEMID$" if exists
    if service_problem_id.find('$') != -1:
        service_problem_id = ''

    # Check if this is a new problem or a recovery
    s4_status = 'new'
    if notification_type == 'RECOVERY':
        s4_status = 'resolved'

    message = {
        'Title': description,
        'HostName': host_name,
        'NotificationType': notification_type,
        'ServiceState': service_state,
        'ServiceDescription': service_desc,
        'ServiceOutput': service_output,
        'HostState': host_state,
        'NotificationComment': notification_comment,
        'ContactName': contact_name,
        'ContactAlias': contact_alias,
        'ContactEmail': contact_email,
        'ContactPager': contact_pager,
        'HostProblemId': host_problem_id,
        'ServiceProblemId': service_problem_id,
        'DateTime': date_time,
        'X-S4-ExternalID': 'Checkmk: ' + host_name + '-' + host_problem_id + '-' + service_problem_id,
        'X-S4-Status': s4_status
    }

    return message

def send_alert(password, message):

    resp = requests.post(api_url + password, params=None, data=json.dumps(message))

    if resp.status_code >= 200 and resp.status_code < 300:
        if resp.text.find('eventId') == -1:
            sys.stdout.write(resp.text)
            sys.exit(0)

    if resp.status_code >= 500 and resp.status_code < 600:
        sys.stderr.write(resp.text)
        sys.exit(1)

    sys.stderr.write(resp.text)
    sys.exit(2)

sys.exit(main())
