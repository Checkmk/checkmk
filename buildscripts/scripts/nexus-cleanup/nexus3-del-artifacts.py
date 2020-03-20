#!/usr/bin/env python3

from nexuscli import cli
import types
import re
from datetime import date, timedelta, datetime
import argparse


# Setup the connection to nexus
def setup_client(url, user, pwd):
    config = cli.util.NexusConfig(url=url, username=user, password=pwd)
    client = cli.util.NexusClient(config=config)
    return client


# Filter the list of artifacts for matching patterns
def filter_artifacts(artifact_list, patterns):
    matching_artifacts = []
    if not isinstance(artifact_list, (list, types.GeneratorType)):
        return []
    for artifact in artifact_list:
        for pattern in patterns:
            match = re.findall(pattern, artifact)
            if match:
                matching_artifacts.append(artifact)
                # Exit loop on first match so no dupplets end up in final list
                break
    return matching_artifacts


def default_patterns():
    patterns = []
    yesterday = date.today() - timedelta(days=1)
    patterns.append('c.e-' + yesterday.strftime('%Y.%m.%d'))
    # Delete all Sandbox Branches on Saturdays
    if (datetime.today().weekday() == 5):
        patterns.append('sandbox')
    return patterns


# Parse Arguments
parser = argparse.ArgumentParser(
    description="Search and delte Artifacts from Nexus3 Artifact Store")
parser.add_argument("url", help="URL of the Nexus Artifact Store")
parser.add_argument("user", help="Username to log in to the Nexus Artifact Store")
parser.add_argument("pwd", help="Password to log in to the Nexus Artifact Store")
parser.add_argument("--repo", help="Set Repo to search and delete files. The default is 'docker'")
parser.add_argument(
    "--pattern",
    help=
    "Set pattern to search and delete files. By default yesterdays temporary images and on Saturdays sandbox images are deleted."
)
args = parser.parse_args()

# Login to Nexus
client = setup_client(args.url, args.user, args.pwd)

# Set Repo to use
if args.repo:
    repo = args.repo
else:
    repo = 'docker'

# Get a list of all artifacts
artifact_list = client.list(repo)

# patterns to be delted
if args.pattern:
    patterns = [args.pattern]
else:
    patterns = default_patterns()

print('Patterns to be deleted:')
print(patterns)
matching_artifacts = filter_artifacts(artifact_list, patterns)
print('Matching artifacts:')
print(matching_artifacts)
for artifact in matching_artifacts:
    client.delete(repo + '/' + artifact)
