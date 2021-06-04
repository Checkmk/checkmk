#!/usr/bin/env python3
"""What would Gerrit do?

This script evaluates a YAML file containing dynamic information about Jenkins pipeline stages
and environmental conditions (e.g. changed files since last commit) and generates a static list
of stages (i.e. without any variables left to evaluate).
This list can either be executed directly or returned (JSON encoded on stdout or in file) in order
to be read and handled later by a Jenkins pipelined job.
"""

from typing import TypedDict, Tuple, Dict, Mapping, Sequence, Any
import sys
import os
from functools import reduce
import subprocess
import json
import yaml
import argparse
import logging
from pathlib import Path

LOG = logging.getLogger("validate_changes")

Vars = Mapping[str, str]  # Just a shortcut for generic str -> str mapping


class StageInfo(TypedDict, total=False):
    """May contain a raw or finalized info set for a Jenkins pipeline stage"""
    NAME: str
    ONLY_WHEN_NOT_EMPTY: str
    DIR: str
    ENV_VARS: Mapping[str, str]
    ENV_VAR_LIST: Sequence[str]
    COMMAND: str
    TEXT_ON_SKIP: str
    SKIPPED: str


Stages = Sequence[StageInfo]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments and return argument object"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-level",
        "-l",
        type=str.upper,
        default='INFO',
        help="Set the minimum level for debug messages",
    )
    parser.add_argument(
        "--env",
        "-e",
        type=str,
        default=[],
        action='append',
        help="Set a variable to be used to expand commands",
    )
    parser.add_argument(
        "--write-file",
        "-w",
        type=str,
        help="Don't execute the stages but write a JSON encoded list of stages to"
        " given file ('-' for stdout",
    )
    parser.add_argument(
        "--no-skip",
        type=lambda a: a.lower() in {"1", "true"},
        default=False,
        help="Ignore conditions for skipping stages (activate all)",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A YAML encoded file containing information about stages to generate",
    )
    return parser.parse_args()


def to_stage_info(raw_stage: Mapping[Any, Any]) -> StageInfo:
    """Return StageInfo created from validated @raw_stage"""
    return StageInfo(
        NAME=str(raw_stage["NAME"]),
        ONLY_WHEN_NOT_EMPTY=str(raw_stage.get("ONLY_WHEN_NOT_EMPTY", "")),
        DIR=str(raw_stage.get("DIR", "")),
        ENV_VARS={str(k): str(v) for k, v in raw_stage.get("ENV_VARS", {}).items()},
        COMMAND=str(raw_stage["COMMAND"]),
        TEXT_ON_SKIP=str(raw_stage.get("TEXT_ON_SKIP", "")),
    )


def load_file(filename: Path) -> Tuple[Sequence[Vars], Stages]:
    """Read and parse a YAML file containing 'VARIABLES' and 'STAGES' and return a tuple with
    typed content"""
    raw_data = yaml.load(open(filename), Loader=yaml.BaseLoader)
    return (
        [{str(k): str(v) for k, v in e.items()} for e in raw_data["VARIABLES"]],
        list(map(to_stage_info, raw_data["STAGES"])),
    )


def replace_variables(string: str, env_vars: Vars) -> str:
    """Replace all occurrences of '${VAR_NAME}' in @string based on @env_vars
    >>> replace_variables("foo: ${foo}", {"foo": "bar"})
    'foo: bar'
    """
    return reduce(lambda s, kv: str.replace(s, f"${{{kv[0]}}}", kv[1]), env_vars.items(), string)


def apply_variables(in_data: StageInfo, env_vars: Vars) -> StageInfo:
    """Apply variables to a stage info set. Make sure the ENV_VARS sub-mapping gets handled."""
    return StageInfo(
        NAME=replace_variables(in_data["NAME"], env_vars),
        ONLY_WHEN_NOT_EMPTY=replace_variables(in_data["ONLY_WHEN_NOT_EMPTY"], env_vars),
        DIR=replace_variables(in_data["DIR"], env_vars),
        ENV_VARS={k: replace_variables(v, env_vars) for k, v in in_data["ENV_VARS"].items()},
        COMMAND=replace_variables(in_data["COMMAND"], env_vars),
        TEXT_ON_SKIP=replace_variables(in_data["TEXT_ON_SKIP"], env_vars),
    )


def finalize_stage(stage: StageInfo, env_vars: Vars, no_skip: bool) -> StageInfo:
    """Return an updated list of stages with conditions applied and values reformatted"""
    condition_vars = stage.get("ONLY_WHEN_NOT_EMPTY")
    skip_stage = condition_vars and not any(env_vars[v] for v in condition_vars.split(","))
    result = (
        StageInfo(
            NAME=stage["NAME"],
            DIR=stage.get("DIR", ""),
            ENV_VAR_LIST=[f"{k}={v}" for k, v in stage.get("ENV_VARS", {}).items()],
            COMMAND=stage["COMMAND"],
        ) if no_skip or not skip_stage else  #
        StageInfo(
            NAME=stage["NAME"],
            SKIPPED=(f'Reason: {stage.get("TEXT_ON_SKIP") or "not provided"},'
                     f' Condition: {condition_vars}'),
        ))

    # todo: remove
    assert not any(isinstance(v, str) and "${" in v for v in result.values())
    assert not any("${" in v for v in result.get("ENV_VAR_LIST", []))

    return result


def run_shell_command(cmd: str, replace_newlines: bool) -> str:
    stdout_str = subprocess.check_output(["sh", "-c", cmd], universal_newlines=True).strip()
    return stdout_str.replace("\n", " ") if replace_newlines else stdout_str


def evaluate_vars(raw_vars: Sequence[Vars], env_vars: Vars) -> Vars:
    """Evaluate receipts for variables. Make sure already evaluated variables can be used in
    later steps.
    >>> evaluate_vars([
    ...    {"NAME": "FOO", "SH": "echo foo ${FIRST}"},
    ...    {"NAME": "BAR", "SH": "echo bar ${FOO}"},
    ...    {"NAME": "VOLATILE", "SH": "echo default"},
    ...  ],
    ...  {
    ...    "FIRST": "first",
    ...    "SECOND": "second",
    ...    "VOLATILE": "overwritten",
    ... })
    {'FIRST': 'first', 'SECOND': 'second', 'VOLATILE': 'overwritten', 'FOO': 'foo first', 'BAR': 'bar foo first'}
    """
    result: Dict[str, str] = dict(env_vars)
    for e in raw_vars:
        # .setdefault() is used to ensure values once written do not get overwritten. This way
        # we can start with variables provided on command line (and already using them)
        cmd = replace_variables(e["SH"], result)

        assert "${" not in cmd # todo: remove

        LOG.debug("evaluate %r run command %r", e["NAME"], cmd)
        cmd_result = run_shell_command(cmd, bool(e.get("REPLACE_NEWLINES")))
        LOG.debug("set to %r", cmd_result)
        result.setdefault(e["NAME"], cmd_result)

    # todo: remove
    assert not any("${" in v for v in result.values())

    return result


def compile_stage_info(stages_file: Path, env_vars: Vars, no_skip: bool) -> Tuple[Vars, Stages]:
    """Return a list of stages loaded from provided YAML file with variables applied"""
    raw_vars, raw_stages = load_file(stages_file)
    finalized_vars = evaluate_vars(raw_vars, env_vars)
    return (
        finalized_vars,
        [
            finalize_stage(
                apply_variables(stage, finalized_vars),
                finalized_vars,
                no_skip,
            ) for stage in raw_stages
        ],
    )


def run_locally(stages: Stages) -> None:
    """Not yet implementd: run all stages by executing each command"""
    print("NYI")
    for s in stages:
        print(f"{s['NAME']}: {s.get('COMMAND', 'SKIPPED: ' + s.get('SKIPPED', ''))}")


def main() -> None:
    """Generate and either process or write a static list of stages"""
    args = parse_args()
    logging.basicConfig(
        format="%(levelname)s %(name)s %(asctime)s: %(message)s",
        datefmt='%H:%M:%S',
        level=getattr(logging, args.log_level),
    )
    LOG.debug("Python: %s %s", '.'.join(map(str, sys.version_info)), sys.executable)
    LOG.debug("Args: %s", args.__dict__)
    env_vars = {key: value for var in args.env for key, value in (var.split("=", 1),)}
    LOG.debug("Variables: %s", env_vars)
    LOG.debug("LC_ALL: %s", os.environ.get("LC_ALL"))
    variables, stages = compile_stage_info(args.input, env_vars, args.no_skip)
    if args.write_file:
        json.dump(
            obj={
                "VARIABLES": variables,
                "STAGES": stages,
            },
            fp=sys.stdout if args.write_file == "-" else open(args.write_file, "w"),
            indent=2,
        )
    else:
        run_locally(stages)


if __name__ == "__main__":

    # kommt weg
    import doctest
    assert not doctest.testmod().failed

    main()
