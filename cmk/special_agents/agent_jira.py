#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | "_ \ / _ \/ __| |/ /   | |\/| | " /            |
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

import argparse
import json
import logging
import sys
from requests.exceptions import ConnectionError as RequestsConnectionError
import urllib3  # type: ignore
from jira import JIRA  # type: ignore[import]
from jira.exceptions import JIRAError  # type: ignore[import]

urllib3.disable_warnings(urllib3.exceptions.SubjectAltNameWarning)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    setup_logging(args.verbose)

    try:
        logging.info('Start constructing connection settings')
        jira = _handle_jira_connection(args)
    except RequestsConnectionError as connection_error:
        sys.stderr.write("Error connecting Jira server: %s\n" % connection_error)
        if args.debug:
            raise
        return 1

    try:
        _handle_request(args, jira)
    except Exception as unknown_error:
        sys.stderr.write("Unhandled exception: %s\n" % unknown_error)
        if args.debug:
            raise
        return 1

    return 0


def _handle_jira_connection(args):
    jira_url = "%s://%s/" % (args.proto, args.hostname)

    jira = JIRA(
        server=jira_url,
        basic_auth=(args.user, args.password),
        options={'verify': False},
        max_retries=0,
    )

    return jira


def _handle_request(args, jira):
    if args.project_workflows_key:

        logging.info('Retrieving workflow data')
        workflow_output = _handle_project(jira, args)
        if workflow_output is not None:
            sys.stdout.write("%s\n" % workflow_output)

    if args.jql_result:

        logging.info('Retrieving custom service data')
        custom_query_output = _handle_custom_query(jira, args)
        if custom_query_output is not None:
            sys.stdout.write("%s\n" % custom_query_output)


def _handle_project(jira, args):
    projects = [{
        'Name': k,
        'Workflow': v
    } for k, v in zip(
        args.project_workflows_key,
        args.project_workflows_values,
    )]

    # get open issues for each project and workflow
    sys.stdout.write("<<<jira_workflow>>>\n")
    issues_dict = {}
    for project in projects:
        project_name = project["Name"][0]
        for workflow in project.get("Workflow", []):

            max_results = 0
            startat = 0
            field = None
            svc_desc = None
            jql = "project = '%s' AND status = '%s'" % (project_name, workflow)
            issues = _handle_search_issues(
                jira,
                jql,
                field,
                startat,
                max_results,
                args,
                project_name,
                svc_desc,
            )
            if issues is None:
                continue
            issues_dict.setdefault(project_name, {}).update({workflow: len(issues)})

    if issues_dict:
        return json.dumps(issues_dict)

    return


def _handle_custom_query(jira, args):
    projects = [{
        'Description': d,
        'Query': q,
        'Field': f,
        'Result': r,
        'Limit': l,
    } for d, q, f, r, l in zip(
        args.jql_desc,
        args.jql_query,
        args.jql_field,
        args.jql_result,
        args.jql_limit,
    )]

    sys.stdout.write("<<<jira_custom_svc>>>\n")
    result_dict = {}
    for query in projects:

        jql = query["Query"][0]
        max_results = query["Limit"][0]
        svc_desc = query["Description"][0]
        field = query["Field"][0]
        startat = None
        project = None
        if field == "None":
            # count number of search results
            max_results = 0
            startat = 0
            field = None
            issues = _handle_search_issues(
                jira,
                jql,
                field,
                startat,
                max_results,
                args,
                project,
                svc_desc,
            )
            if issues is None:
                continue
            result_dict.setdefault(svc_desc, {}).update({"count": len(issues)})
            continue

        issues = _handle_search_issues(
            jira,
            jql,
            field,
            startat,
            max_results,
            args,
            project,
            svc_desc,
        )
        if issues is None:
            continue

        total = 0
        for issue in issues:
            search_field = getattr(issue.fields, field)
            total += search_field if search_field and isinstance(search_field, float) else 0

        if query["Result"][0] == "sum":
            key = "sum"
            value = total
        else:
            # average
            key = "avg"
            value = "%.2f" % (total / len(issues))

        result_dict.setdefault(svc_desc, {}).update({key: value})

    if result_dict:
        return json.dumps(result_dict)

    return


def _handle_search_issues(jira, jql, field, startat, max_results, args, project, svc_desc):
    try:
        issues = jira.search_issues(jql,
                                    startAt=startat,
                                    maxResults=max_results,
                                    json_result=False,
                                    fields=field,
                                    validate_query=True)
    except JIRAError as jira_error:
        # errors of sections are handled and shown by/in the related checks
        msg = "Jira error %s: %s" % (jira_error.status_code, jira_error.text)
        if project:
            key = project
        else:
            key = svc_desc
        msg_dict = {key: {"error": msg}}
        sys.stdout.write("%s\n" % json.dumps(msg_dict))
        if args.debug:
            raise
    else:
        return issues


def setup_logging(verbosity):
    # type: (int) -> None
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format='%(asctime)s %(levelname)s %(message)s')


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--debug",
                        action="store_true",
                        help='''Debug mode: raise Python exceptions''')
    parser.add_argument('-v',
                        '--verbose',
                        action='count',
                        default=0,
                        help='Verbose mode (for even more output use -vvv)')
    parser.add_argument("-P",
                        "--proto",
                        default="https",
                        required=True,
                        help="Use 'http' or 'https' for connection to Jira (default=https)")
    parser.add_argument("-u", "--user", default=None, required=True, help="Username for Jira login")
    parser.add_argument("-s",
                        "--password",
                        default=None,
                        required=True,
                        help="Password for Jira login")
    parser.add_argument('--project-workflows-key',
                        nargs=1,
                        action='append',
                        help="The full project name")
    parser.add_argument('--project-workflows-values',
                        nargs='+',
                        action='append',
                        help="The names of workflows of the given project")
    parser.add_argument('--jql-desc', nargs=1, action='append', help="Service description.")
    parser.add_argument('--jql-query', nargs=1, action='append', help="JQL search string.")
    parser.add_argument('--jql-result',
                        nargs=1,
                        action='append',
                        choices=('count', 'sum', 'average'),
                        help='Search result to use. You can show the number of '
                        'search results (\"count\") or the summed up (\"sum\") or '
                        'average values (\"average\") of a given numeric field.')
    parser.add_argument('--jql-field',
                        nargs=1,
                        action='append',
                        help='Field for operation. Please use \"None\" if you '
                        'use \"count\" as result option.')
    parser.add_argument('--jql-limit',
                        nargs=1,
                        action='append',
                        help="Maximum number of processed search results.")
    parser.add_argument("--hostname", required=True, help="JIRA server to use")

    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
