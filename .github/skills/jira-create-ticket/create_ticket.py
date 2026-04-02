#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Self-contained script to create a Jira ticket in the CMK project.

Usage:
    JIRA_API_TOKEN=your-token python3 create_ticket.py \
        --summary "Fix the broken widget" \
        --description "The widget crashes when clicking save" \
        [--issue-type Story] \
        [--component "REST API"] \
        [--developer-team "Platform"] \
        [--priority "Major"] \
        [--parent CMK-12345] \
        [--link-epic CMK-99999] \
        [--dry-run]

    # List all open roadmap epics (for LLM context)
    python3 create_ticket.py --find-epics --summary "unused but required"
"""

import argparse
import json
import os
import sys
import urllib.request
from typing import Any

# ---------------------------------------------------------------------------
# Jira authentication (copied from create_issue.py)
# ---------------------------------------------------------------------------

JIRA_SERVER = "https://jira.lan.tribe29.com"
JIRA_TOKEN_VAR = "JIRA_API_TOKEN"
COMPASS_JSON_URL = "https://devdocs.lan.checkmk.net/developer_matrix/compass.json"


def _get_token_from_env(env_var: str) -> str:
    token = os.environ.get(env_var)
    if not token:
        raise ValueError(f"Environment variable {env_var} is not set")
    return token


def _connect_jira(jira_server: str, jira_api_key: str) -> Any:
    from jira import JIRA

    try:
        return JIRA(server=jira_server, token_auth=jira_api_key)
    except Exception:
        raise ConnectionError("Jira connection could not be established")


# ---------------------------------------------------------------------------
# Component / team guessing from compass JSON endpoint
# ---------------------------------------------------------------------------


def _fetch_compass_json(url: str) -> list[dict[str, Any]]:
    """Fetch the compass JSON from a URL. Exits if the endpoint is unreachable."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            result: list[dict[str, Any]] = json.loads(resp.read().decode("utf-8"))
            return result
    except Exception as e:
        print(f"ERROR: Cannot fetch compass JSON from {url}: {e}", file=sys.stderr)
        sys.exit(1)


def list_components(compass_url: str) -> list[dict[str, Any]]:
    """Return a compact list of all components from the compass JSON endpoint.

    Each entry contains: name, teams, and a truncated description (if available).
    Designed to be printed as JSON for LLM context — the LLM picks the best match.
    """
    components = _fetch_compass_json(compass_url)
    result = []
    for comp in components:
        entry: dict[str, Any] = {
            "name": comp.get("name", ""),
            "teams": comp.get("teams", []),
        }
        desc = (comp.get("description") or "").strip()
        if desc and desc != "-":
            entry["description"] = desc[:150]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Epic search — find open epics that might be parents for a new ticket
# ---------------------------------------------------------------------------


def find_epics(jira: Any) -> list[dict[str, str]]:
    """Return all open roadmap epics in CMK as a flat list.

    Uses the roadmap hierarchy rooted at CMK-24875 to find only epics that
    are part of the roadmap (Roadmap Ticket -> Business Goal -> Initiative -> Epic).

    Returns a list of dicts with keys: key, summary, components, team, status.
    No scoring or ranking — the LLM picks the best match from the full list.
    """
    jql = (
        'issueFunction in linkedIssuesOfAllRecursive("issuekey = CMK-24875", '
        '"is implemented by", "is Epic of") '
        "AND project in (checkmk) AND type = Epic AND resolution is EMPTY "
        "ORDER BY issuetype DESC, status ASC"
    )

    try:
        issues = jira.search_issues(
            jql,
            maxResults=200,
            fields="summary,components,status,customfield_11500",
        )
    except Exception as e:
        print(f"WARNING: Epic search failed: {e}", file=sys.stderr)
        return []

    results: list[dict[str, str]] = []
    for issue in issues:
        components_list = [c.name for c in (issue.fields.components or [])]
        team_field = getattr(issue.fields, "customfield_11500", None)
        team_value = team_field.value if team_field else ""
        results.append(
            {
                "key": issue.key,
                "summary": issue.fields.summary or "",
                "components": ", ".join(components_list),
                "team": team_value,
                "status": str(issue.fields.status),
            }
        )

    return results


# ---------------------------------------------------------------------------
# Jira custom field IDs
# ---------------------------------------------------------------------------

CUSTOM_FIELDS = {
    "developer_team": "customfield_11500",  # select
    "storypoints": "customfield_10106",  # number
    "epic_link": "customfield_10100",  # any (Epic Link on Stories/Bugs/Tasks)
    "epic_name": "customfield_10102",  # text
    "technical_owner": "customfield_13601",  # user
    "initiative_owner": "customfield_13600",  # user
    "initiative_sponsor": "customfield_13602",  # user
}

# ---------------------------------------------------------------------------
# Issue creation
# ---------------------------------------------------------------------------


def create_issue(
    jira: Any,
    *,
    project: str,
    issue_type: str,
    summary: str,
    description: str,
    component: str | None = None,
    developer_team: str | None = None,
    priority: str | None = None,
    parent: str | None = None,
    link_epic: str | None = None,
) -> Any:
    fields: dict[str, Any] = {
        "project": {"key": project},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
        "labels": ["jira-create-ticket"],
    }

    if component:
        fields["components"] = [{"name": component}]

    if developer_team:
        fields[CUSTOM_FIELDS["developer_team"]] = {"value": developer_team}

    if priority:
        fields["priority"] = {"name": priority}

    if parent:
        fields["parent"] = {"key": parent}

    if issue_type == "Epic":
        fields[CUSTOM_FIELDS["epic_name"]] = summary

    if link_epic:
        fields[CUSTOM_FIELDS["epic_link"]] = link_epic

    issue = jira.create_issue(fields=fields)

    return issue


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Jira ticket in CMK")
    parser.add_argument("--summary", default="", help="Issue summary/title (required for create)")
    parser.add_argument("--description", default="", help="Issue description (Jira wiki markup)")
    parser.add_argument(
        "--issue-type", default="Task", help="Issue type: Task or Bug (default: Task)"
    )
    parser.add_argument("--project", default="CMK", help="Jira project key (default: CMK)")
    parser.add_argument("--component", default=None, help="Jira component name")
    parser.add_argument("--developer-team", default=None, help="Developer Team field value")
    parser.add_argument("--priority", default=None, help="Priority (e.g. Major, Minor, Critical)")
    parser.add_argument("--parent", default=None, help="Parent issue key (e.g. CMK-12345)")
    parser.add_argument(
        "--link-epic", default=None, help="Epic key to link as parent (e.g. CMK-12345)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print fields without creating")
    parser.add_argument(
        "--guess", action="store_true", help="Print all compass components as JSON and exit"
    )
    parser.add_argument(
        "--find-epics",
        action="store_true",
        help="Print all open roadmap epics as JSON and exit",
    )

    args = parser.parse_args()

    # List components mode — dump compass data for LLM context
    if args.guess:
        components = list_components(COMPASS_JSON_URL)
        print(json.dumps(components, indent=2))
        sys.exit(0)

    # Epic search mode — dump all open roadmap epics for LLM context
    if args.find_epics:
        token = _get_token_from_env(JIRA_TOKEN_VAR)
        jira = _connect_jira(JIRA_SERVER, token)
        epics = find_epics(jira)
        print(json.dumps(epics, indent=2))
        sys.exit(0)

    component = args.component
    developer_team = args.developer_team

    if args.dry_run:
        print("=== DRY RUN — would create issue with: ===")
        print(
            json.dumps(
                {
                    "project": args.project,
                    "issue_type": args.issue_type,
                    "summary": args.summary,
                    "description": args.description,
                    "component": component,
                    "developer_team": developer_team,
                    "priority": args.priority,
                    "parent": args.parent,
                    "labels": ["jira-create-ticket"],
                    "link_epic": args.link_epic,
                },
                indent=2,
            )
        )
        sys.exit(0)

    token = _get_token_from_env(JIRA_TOKEN_VAR)
    jira = _connect_jira(JIRA_SERVER, token)

    issue = create_issue(
        jira,
        project=args.project,
        issue_type=args.issue_type,
        summary=args.summary,
        description=args.description,
        component=component,
        developer_team=developer_team,
        priority=args.priority,
        parent=args.parent,
        link_epic=args.link_epic,
    )

    url = f"{JIRA_SERVER}/browse/{issue.key}"
    print(f"Created: {issue.key} — {url}")
    if args.link_epic:
        print(f"Linked to epic: {args.link_epic}")


if __name__ == "__main__":
    main()
