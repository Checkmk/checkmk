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

# - adds an issue if no issue exists
# - set resolution in existing issue on recovery notification (if option is set)

import sys
from jira import JIRA  # type: ignore
from jira.exceptions import JIRAError  # type: ignore
import urllib3  # type: ignore
from cmk.notification_plugins import utils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    context = utils.collect_context()
    tmpl_host_summary = 'Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$'
    tmpl_service_summary = 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$'
    tmpl_label = 'monitoring'

    for necessary in [
            'PARAMETER_URL', 'PARAMETER_USERNAME', 'PARAMETER_PASSWORD', 'PARAMETER_HOST_CUSTOMID',
            'PARAMETER_SERVICE_CUSTOMID'
    ]:
        if necessary not in context:
            sys.stderr.write("%s not set" % necessary)
            return 2

    if "PARAMETER_IGNORE_SSL" in context:
        sys.stdout.write("Unverified HTTPS request warnings are ignored. Use with caution.\n")
        jira = JIRA(server=context['PARAMETER_URL'],
                    basic_auth=(context['PARAMETER_USERNAME'], context['PARAMETER_PASSWORD']),
                    options={'verify': False})
    else:
        jira = JIRA(server=context['PARAMETER_URL'],
                    basic_auth=(context['PARAMETER_USERNAME'], context['PARAMETER_PASSWORD']))

    if context['WHAT'] == 'HOST':
        summary = context.get('PARAMETER_HOST_SUMMARY') or tmpl_host_summary
        svc_desc = context['HOSTOUTPUT']
        custom_field = int(context['PARAMETER_HOST_CUSTOMID'])
        custom_field_value = int(context['HOSTPROBLEMID'])
    else:
        summary = context.get('PARAMETER_SERVICE_SUMMARY') or tmpl_service_summary
        svc_desc = context['SERVICEOUTPUT']
        custom_field = int(context['PARAMETER_SERVICE_CUSTOMID'])
        custom_field_value = int(context['SERVICEPROBLEMID'])

    context['SUBJECT'] = utils.substitute_context(summary, context)
    label = context.get('PARAMETER_LABEL') or tmpl_label
    newissue = {
        u'labels': [label],
        u'summary': context['SUBJECT'],
        u'description': svc_desc,
    }

    if 'PARAMETER_PROJECT' in context:
        newissue[u'project'] = {u'id': context['PARAMETER_PROJECT']}
    if 'CONTACT_JIRAPROJECT' in context:
        newissue[u'project'] = {u'id': context['CONTACT_JIRAPROJECT']}
    if 'PARAMETER_ISSUETYPE' in context:
        newissue[u'issuetype'] = {u'id': context['PARAMETER_ISSUETYPE']}
    if 'CONTACT_JIRAISSUETYPE' in context:
        newissue[u'issuetype'] = {u'id': context['CONTACT_JIRAISSUETYPE']}
    if 'PARAMETER_PRIORITY' in context:
        newissue[u'priority'] = {u'id': context['PARAMETER_PRIORITY']}
    if 'CONTACT_JIRAPRIORITY' in context:
        newissue[u'priority'] = {u'id': context['CONTACT_JIRAPRIORITY']}
    if 'project' not in newissue:
        sys.stderr.write("No JIRA project ID set, discarding notification")
        return 2
    if 'issuetype' not in newissue:
        sys.stderr.write("No JIRA issue type ID set")
        return 2

    try:
        custom_field_exists = jira.search_issues("cf[%d]=%d" % (custom_field, custom_field_value))
    except JIRAError as err:
        sys.stderr.write('Unable to query custom field search, JIRA response code %s, %s' %
                         (err.status_code, err.text))
        return 2

    if not custom_field_exists:
        newissue[u'customfield_%d' % custom_field] = custom_field_value

    if context['NOTIFICATIONTYPE'] == 'PROBLEM':
        try:
            issue = jira.create_issue(fields=newissue)
        except JIRAError as err:
            sys.stderr.write('Unable to create issue, JIRA response code %s, %s' %
                             (err.status_code, err.text))
            return 2
        sys.stdout.write('Created %s\n' % issue.permalink())
        if 'PARAMETER_MONITORING' in context:
            if context['PARAMETER_MONITORING'].endswith('/'):
                # remove trailing slash
                context['PARAMETER_MONITORING'] = context['PARAMETER_MONITORING'][:-1]
            if context['WHAT'] == 'SERVICE':
                url = context['PARAMETER_MONITORING'] + context['SERVICEURL']
            else:
                url = context['PARAMETER_MONITORING'] + context['HOSTURL']
            try:
                rl = jira.add_simple_link(issue, {'url': url, 'title': 'Monitoring'})
            except JIRAError as err:
                sys.stderr.write('Unable to create link in issue, JIRA response code %s, %s\n' %
                                 (err.status_code, err.text))
                return 2
            sys.stdout.write('Created JIRA simple link: %s' % rl)

    if context['NOTIFICATIONTYPE'] == 'RECOVERY' and custom_field_exists:
        if "PARAMETER_RESOLUTION" not in context:
            sys.stderr.write(
                "Ticket resolution not enabled in wato rule. Don't send a resolution to jira\n")
            return 0
        else:
            resolution = None
            if 'PARAMETER_RESOLUTION' in context:
                resolution = context['PARAMETER_RESOLUTION']
            if 'CONTACT_JIRARESOLUTION' in context:
                resolution = context['CONTACT_JIRARESOLUTION']
            if resolution is None:
                sys.stderr.write("No JIRA resolution ID set")
                return 2
        for issue in custom_field_exists:
            try:
                jira.transition_issue(issue, resolution, comment=newissue['description'])
                sys.stdout.write('Resolved %s' % issue.permalink())
            except JIRAError as err:
                sys.stderr.write('Unable to resolve %s, JIRA response code %s, %s' %
                                 (issue.permalink(), err.status_code, err.text))
                return 2
