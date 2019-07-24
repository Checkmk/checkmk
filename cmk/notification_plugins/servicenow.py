# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
import requests
from cmk.notification_plugins import utils
from cmk.notification_plugins.utils import retrieve_from_passwordstore

PRIORITY_STATES = {
    "low": 3,
    "medium": 2,
    "high": 1,
}

COMMAND_STATES = {
    "none": 0,
    "new": 1,
    "progress": 2,
    "hold": 3,
    "resolved": 4,
    "closed": 5,
    "canceled": 6,
}


def main():
    context = utils.collect_context()
    timeout = 10
    urgency = 3
    impact = 3
    ack_state = 0
    dtstart_state = 0
    dtend_state = 0

    for necessary in [
            'PARAMETER_URL', 'PARAMETER_USERNAME', 'PARAMETER_PASSWORD', 'PARAMETER_CALLER'
    ]:
        if necessary not in context:
            sys.stderr.write("%s not set\n" % necessary)
            return 2

    hostname = context['HOSTNAME']
    url = context['PARAMETER_URL']
    proxy_url = context.get("PARAMETER_PROXY_URL")
    proxies = {"https": proxy_url} if proxy_url else None
    user = context['PARAMETER_USERNAME']
    pwd = retrieve_from_passwordstore(context['PARAMETER_PASSWORD'])
    caller = context['PARAMETER_CALLER']

    if 'PARAMETER_TIMEOUT' in context:
        timeout = float(context['PARAMETER_TIMEOUT'])
    if 'PARAMETER_URGENCY' in context:
        urgency = PRIORITY_STATES[context['PARAMETER_URGENCY']]
    if 'PARAMETER_IMPACT' in context:
        impact = PRIORITY_STATES[context['PARAMETER_IMPACT']]
    if 'PARAMETER_ACK_STATE_START' in context:
        ack_state = COMMAND_STATES[context['PARAMETER_ACK_STATE_START']]
    if 'PARAMETER_DT_STATE_START' in context:
        dtstart_state = COMMAND_STATES[context['PARAMETER_DT_STATE_START']]
    if 'PARAMETER_DT_STATE_END' in context:
        dtend_state = COMMAND_STATES[context['PARAMETER_DT_STATE_END']]
    if context['WHAT'] == 'HOST':
        tmpl_host_short_desc = 'Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$'
        tmpl_host_desc = """Host: $HOSTNAME$
Event:    $EVENT_TXT$
Output:   $HOSTOUTPUT$
Perfdata: $HOSTPERFDATA$
$LONGHOSTOUTPUT$
"""
        short_desc = context.get('PARAMETER_HOST_SHORT_DESC') or tmpl_host_short_desc
        desc = context.get('PARAMETER_HOST_DESC') or tmpl_host_desc
        problem_id = context['HOSTPROBLEMID']
        ack_author = context['HOSTACKAUTHOR']
        ack_comment = context['HOSTACKCOMMENT']
        servicename = context['HOSTOUTPUT']
    else:
        tmpl_svc_short_desc = 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$'
        tmpl_svc_desc = """Host: $HOSTNAME$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$
Perfdata: $SERVICEPERFDATA$
$LONGSERVICEOUTPUT$
"""
        short_desc = context.get('PARAMETER_SVC_SHORT_DESC') or tmpl_svc_short_desc
        servicename = context['SERVICEDESC']
        desc = context.get('PARAMETER_SVC_DESC') or tmpl_svc_desc
        problem_id = context['SERVICEPROBLEMID']
        ack_author = context['SERVICEACKAUTHOR']
        ack_comment = context['SERVICEACKCOMMENT']

    short_desc = utils.substitute_context(short_desc, context)
    desc = utils.substitute_context(desc, context)
    incident = handle_issue_exists(problem_id, proxies, url, user, pwd)

    if context['NOTIFICATIONTYPE'] == 'PROBLEM':
        if incident:
            sys.stdout.write(
                "Ticket %s with Check_MK problem ID: %s in work notes already exists.\n" %
                (incident[0], problem_id))
            return 0
        handle_problem(url, proxies, user, pwd, short_desc, desc, hostname, servicename, problem_id,
                       caller, urgency, impact, timeout)
    elif context['NOTIFICATIONTYPE'] == 'RECOVERY':
        handle_recovery(incident, url, proxies, user, pwd, desc, caller, timeout)
    elif context['NOTIFICATIONTYPE'] == 'ACKNOWLEDGEMENT':
        handle_ack(incident, url, proxies, user, pwd, ack_comment, ack_author, ack_state, caller,
                   timeout)
    elif context['NOTIFICATIONTYPE'] == 'DOWNTIMESTART':
        desc = """Downtime was set.
User: $NOTIFICATIONAUTHOR$
Comment: $NOTIFICATIONCOMMENT$
"""
        desc = utils.substitute_context(desc, context)
        handle_downtime(incident, url, proxies, user, pwd, desc, dtstart_state, caller, timeout)
        sys.stdout.write('Ticket %s: successfully added downtime.\n' % incident[0])
    elif context['NOTIFICATIONTYPE'] == 'DOWNTIMEEND':
        desc = """Downtime ended.
"""
        handle_downtime(incident, url, proxies, user, pwd, desc, dtend_state, caller, timeout)
        sys.stdout.write('Ticket %s: successfully removed downtime.\n' % incident[0])
    elif context['NOTIFICATIONTYPE'] == 'DOWNTIMECANCELLED':
        desc = """Downtime canceled.
"""
        handle_downtime(incident, url, proxies, user, pwd, desc, dtend_state, caller, timeout)
        sys.stdout.write('Ticket %s: successfully cancelled downtime.\n' % incident[0])
    else:
        sys.stdout.write("Noticication type %s not supported\n" % (context['NOTIFICATIONTYPE']))
        return 0


def handle_problem(url, proxies, user, pwd, short_desc, desc, hostname, servicename, problem_id,
                   caller, urgency, impact, timeout):
    url += "/api/now/table/incident"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.post(url,
                             proxies=proxies,
                             auth=(user, pwd),
                             headers=headers,
                             timeout=timeout,
                             json={
                                 "short_description": short_desc,
                                 "description": desc,
                                 "urgency": urgency,
                                 "impact": impact,
                                 "caller_id": caller,
                                 "work_notes": "Check_MK Problem ID: %s" % problem_id
                             })

    if response.status_code != 201:
        sys.stderr.write('Status: %s\n' % response.status_code)
        return 2

    incident_nr = response.json()["result"]["number"]
    sys.stdout.write('Ticket successfully created with incident number: %s.\n' % incident_nr)
    return 0


def handle_recovery(incident, url, proxies, user, pwd, desc, caller, timeout):
    url += "/api/now/table/incident/%s" % incident[1]
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.put(url,
                            proxies=proxies,
                            auth=(user, pwd),
                            headers=headers,
                            timeout=timeout,
                            json={
                                "close_code": "Closed/Resolved by Check_MK",
                                "state": "7",
                                "caller_id": caller,
                                "close_notes": desc
                            })

    if response.status_code != 200:
        sys.stderr.write('Status: %s\n' % response.status_code)
        return 2

    sys.stdout.write('Ticket %s successfully resolved.\n' % incident[0])
    return 0


def handle_ack(incident, url, proxies, user, pwd, ack_comment, ack_author, ack_state, caller,
               timeout):
    url += "/api/now/table/incident/%s" % incident[1]
    json = {
        "caller_id": caller,
        "work_notes": "Acknowledged by user: %s\nComment: %s" % (ack_author, ack_comment)
    }

    if ack_state != 0:
        json.update({"state": ack_state})

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.put(url,
                            proxies=proxies,
                            auth=(user, pwd),
                            headers=headers,
                            timeout=timeout,
                            json=json)

    if response.status_code != 200:
        sys.stderr.write('Status: %s\n' % response.status_code)
        return 2

    sys.stdout.write('Ticket %s: successfully added acknowledgedment.\n' % incident[0])
    return 0


def handle_downtime(incident, url, proxies, user, pwd, desc, dt_state, caller, timeout):
    url += "/api/now/table/incident/%s" % incident[1]
    json = {"caller_id": caller, "work_notes": desc}

    if dt_state != 0:
        json.update({"state": dt_state})

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    response = requests.put(url, proxies=proxies, auth=(user, pwd), headers=headers, json=json)

    if response.status_code != 200:
        sys.stderr.write('Status: %s\n' % response.status_code)
        return 2

    return 0


def handle_issue_exists(problem_id, proxies, url, user, pwd):
    headers = {"Accept": "application/json"}
    url += '/api/now/table/incident?sysparm_query=work_notesLIKECheck_MK Problem ID: %s' % problem_id
    response = requests.get(url, proxies=proxies, auth=(user, pwd), headers=headers)
    try:
        return response.json()["result"][0]["number"], response.json()["result"][0]["sys_id"]
    except IndexError:
        return None
