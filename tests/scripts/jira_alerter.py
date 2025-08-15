#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A FastAPI-based service for creating Jira issues via REST API.

This script provides a simple HTTP service with endpoints to:
- Check service status (`GET /status`)
- Create Jira issues (`POST /create`)

Usage:
    python jira_alerter.py --jira-url <JIRA_URL>
    [--host <address>] [--port <port>]

Options:
    --jira-url (str, required): Jira URL.
    --host (str, optional): Address to bind to (default: 0.0.0.0).
    --port (int, optional): Port to bind to (default: 8000).
"""

import argparse
import logging
from getpass import getpass
from os import getenv

import uvicorn
from fastapi import FastAPI
from jira import JIRA
from pydantic import BaseModel

LOGGER = logging.getLogger()


class Ticket(BaseModel):
    summary: str
    description: str


class JiraAlerterArgs(argparse.Namespace):
    """Arguments for the Jira Alerter Service."""

    jira_url: str
    host: str
    port: int


class JiraAlerter:
    app = FastAPI()

    def __init__(self, url: str, token: str):
        assert url, "ERROR: Jira URL required!"
        self.url: str = url
        LOGGER.info("Authenticating to %s", self.url)
        assert token, "ERROR: Jira Personal Access token required!"
        self.client = JIRA(
            server=self.url,
            token_auth=token,
        )


def parse_args() -> JiraAlerterArgs:
    """
    Parses command-line arguments for the Jira Alerter service.

    Returns:
        JiraAlerterArgs: An object containing the parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="My Daemon Service")
    parser.add_argument(
        "--jira-url",
        dest="jira_url",
        type=str,
        required=True,
        help="Jira URL",
    )
    parser.add_argument(
        "--host",
        dest="host",
        type=str,
        default="0.0.0.0",
        help="Address to bind to (default: %(default)s).",
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        default=8000,
        help="Port to bind to (default: %(default)s).",
    )
    return parser.parse_args(namespace=JiraAlerterArgs())


def main():
    """
    Main entry point for the Jira Alerter service.

    Parses command-line arguments, initializes the JiraAlerter application, and sets up API endpoints:
    - GET /status: Returns the running status of the service.
    - POST /create: Creates a new Jira issue using provided ticket details.

    Starts the FastAPI application using Uvicorn with specified host and port.
    """
    args = parse_args()
    jira_token = getenv("JIRA_TOKEN") or getpass("Jira Personal Access Token? ")
    jira_alerter = JiraAlerter(url=args.jira_url, token=jira_token)

    @jira_alerter.app.get("/status")
    def status():
        return {"status": "running"}

    @jira_alerter.app.post("/create")
    def create(issue: Ticket) -> None:
        jira_alerter.client.create_issue(
            fields={
                "project": {"key": "CMK"},
                "summary": issue.summary,
                "description": issue.description,
                "issuetype": {"name": "Task"},
            }
        )

    uvicorn.run(jira_alerter.app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
