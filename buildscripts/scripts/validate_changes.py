#!/usr/bin/env python3
"""What would Gerrit do?

This script evaluates a YAML file containing dynamic information about Jenkins pipeline stages
and environmental conditions (e.g. changed files since last commit) and generates a static list
of stages (i.e. without any variables left to evaluate).
This list can either be executed directly or returned (JSON encoded on stdout or in file) in order
to be read and handled later by a Jenkins pipelined job.
"""

from typing import Callable, TypedDict, Tuple, Dict, Mapping, Sequence, Any, Optional, List
import asyncio
import sys
import os
from functools import reduce
import subprocess
import json
import yaml
import argparse
import logging
import time
from pathlib import Path
from distutils.util import strtobool

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
    RESULT_CHECK_TYPE: str
    RESULT_CHECK_FILE_PATTERN: str


Stages = Sequence[StageInfo]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments and return argument object"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose",
        "-v",
        action='count',
        default=0,
        help="Be verbose (can be applied multiple times)",
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
        action='store_true',
        help="Ignore conditions for skipping stages (activate all)",
    )
    parser.add_argument(
        "--exitfirst",
        "-x",
        action='store_true',
        help="Exit on first failing stage command",
    )
    parser.add_argument(
        "--filter-substring",
        "-k",
        type=str,
        default=[],
        action='append',
        help="Filter for substring in stage name",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A YAML encoded file containing information about stages to generate",
        default=Path(os.path.dirname(__file__)) / "stages.yml",
        nargs="?",
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
        RESULT_CHECK_TYPE=str(raw_stage.get("RESULT_CHECK_TYPE", "")),
        RESULT_CHECK_FILE_PATTERN=str(raw_stage.get("RESULT_CHECK_FILE_PATTERN", "")),
    )


def load_file(filename: Path) -> Tuple[Sequence[Vars], Stages]:
    """Read and parse a YAML file containing 'VARIABLES' and 'STAGES' and return a tuple with
    typed content"""
    try:
        raw_data = yaml.load(Path.read_text(filename), Loader=yaml.BaseLoader)
    except FileNotFoundError:
        raise RuntimeError(
            f"Could not find {filename}. Must be a YAML file containing stage declarations.")

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
        RESULT_CHECK_TYPE=replace_variables(in_data["RESULT_CHECK_TYPE"], env_vars),
        RESULT_CHECK_FILE_PATTERN=replace_variables(in_data["RESULT_CHECK_FILE_PATTERN"], env_vars),
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
            RESULT_CHECK_TYPE=stage["RESULT_CHECK_TYPE"],
            RESULT_CHECK_FILE_PATTERN=stage["RESULT_CHECK_FILE_PATTERN"],
        ) if no_skip or not skip_stage else  #
        StageInfo(
            NAME=stage["NAME"],
            SKIPPED=(f'Reason: {stage.get("TEXT_ON_SKIP") or "not provided"},'
                     f' Condition: {condition_vars}'),
        ))

    for key, value in result.items():
        if "${" in str(value):
            raise RuntimeError(
                f"There unexpanded variables left in stage {stage['NAME']}: {key}={value}."
                " Did you forget to provide them with --env?")

    return result


def run_shell_command(cmd: str, replace_newlines: bool) -> str:
    """Run a command and return preprocessed stdout"""
    stdout_str = subprocess.check_output(["sh", "-c", cmd], universal_newlines=True).strip()
    return stdout_str.replace("\n", " ") if replace_newlines else stdout_str


def evaluate_vars(raw_vars: Sequence[Vars], env_vars: Vars) -> Mapping[str, str]:
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
        if e["NAME"] in result:
            LOG.info("Trying to set existing variable %r", e["NAME"])
            continue

        cmd = replace_variables(e["SH"], result)
        if "${" in cmd:
            raise RuntimeError(
                f"There are still unexpanded variables in command: {cmd!r}."
                " Did you forget to provide them with --env?")

        LOG.debug("evaluate %r run command %r", e["NAME"], cmd)
        cmd_result = run_shell_command(cmd, bool(strtobool(e.get("REPLACE_NEWLINES", "false"))))
        LOG.debug("set to %r", cmd_result)
        result[e["NAME"]] = cmd_result

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


async def run_cmd(cmd: str, env: Mapping[str, str], cwd: Optional[str], check: bool,
              stdout_fn: Callable[[str], None],
              stderr_fn: Callable[[str], None]) -> bool:
    """Run a command while continuously capturing its stdout/stdin and printing it out in a
    predefined way for either stdout or stderr"""
    async def process_lines(stream: asyncio.StreamReader, proc_fn: Callable[[str], None]) -> None:
        async for line in stream:
            proc_fn(line.decode().rstrip())

    process = await asyncio.create_subprocess_exec(
        # Use `bash` rather than `sh` in order to provide things like `&>`
        "bash", "-c", cmd,
        cwd=cwd,
        limit = 1024 * 512,  # see https://stackoverflow.com/questions/55457370
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # This is to make Python scripts behave, i.e. not buffer stdout.
        # this works only for Python of course but a general solution would be nice of course.
        # If someone knows a better way to deactivate buffering, drop me a line please.
        env={**os.environ, **{'PYTHONUNBUFFERED': '1'}, **env},
    )

    assert process.stdout and process.stderr
    await asyncio.gather(
        process_lines(process.stdout, stdout_fn),
        process_lines(process.stderr, stderr_fn))
    await process.wait()

    return process.returncode == 0


async def run_locally(stages: Stages, exitfirst: bool, filter_substring: str, verbosity: int) -> None:
    """Not yet implementd: run all stages by executing each command"""
    col = {
        'red': "\033[1;31m",
        'purple': "\033[1;35m",
        'green': "\033[1;32m",
        'bold': "\033[0;37m",
        'reset': "\033[0;0m",
    }
    results = {}
    for stage in stages:
        name = stage['NAME']
        if filter_substring and not any(map(lambda s: s.lower() in name.lower(), filter_substring)):
            results[name] = f"SKIPPED Reason: none of {filter_substring!r} in name"
            print(f"Stage {name!r}: {results[name]}")
            continue

        if "SKIPPED" in stage:
            results[name] = f"SKIPPED {stage['SKIPPED']}"
            print(f"Stage {name!r}: {results[name]}")
            continue

        print(f"RUN stage ======== {col['bold']}{name}{col['reset']} ============")

        for key, value in stage.items():
            LOG.debug("%s: %s", key, value)

        output: List[str] = []

        t_before = time.time()
        cmd_successful = await run_cmd(
            cmd=stage["COMMAND"],
            env=dict(v.split("=", 1) for v in stage['ENV_VAR_LIST']),
            cwd=stage["DIR"] or None,
            check=exitfirst,
            stdout_fn=(lambda l, name=name: (output.append if verbosity == 0 else print)(
                f"{col['bold']}{name}: {col['reset']}{l}")),
            stderr_fn=(lambda l, name=name: (output.append if verbosity == 0 else print)(
                f"{col['bold']}{name}: {col['purple']}stderr:{col['reset']} {l}")),
        )
        duration = time.time() - t_before

        if cmd_successful:
            results[name] = f"{col['green']}SUCCESSFUL{col['reset']} ({duration:.2f}s)"
        else:
            print("The stage failed and here is, what was captured:")
            for line in output:
                print(line)
            result_file_hint = (f" ({stage['RESULT_CHECK_FILE_PATTERN']})"
                                if "RESULT_CHECK_FILE_PATTERN" in stage else "")
            results[name] = f"{col['red']}FAILED{col['reset']} ({duration:.2f}s){result_file_hint}"
            if "RESULT_CHECK_FILE_PATTERN" in stage:
                print(f"Also a result file '{stage['RESULT_CHECK_FILE_PATTERN']}' has been captured:")
                if stage['RESULT_CHECK_FILE_PATTERN'].endswith(".txt"):
                    with open(stage['RESULT_CHECK_FILE_PATTERN']) as err_file:
                        for l in err_file.readlines():
                            print(f"   {col['purple']}>>>{col['reset']} {l.rstrip()}")
                else:
                    # in case we're dealing with an unknown file format we just print the file name
                    print(f"   {col['bold']}{stage['RESULT_CHECK_FILE_PATTERN']}{col['reset']}")
            if exitfirst:
                print(f"{col['red']}Stage {name!r} returned non-zero"
                      f" and you told me to stop if that happens.{col['reset']}")
                break
        print(f"Stage {name!r}: {results[name]}")

    print("Summary:")
    for stage_name, summary  in results.items():
        print(f" {stage_name:24s} | {summary}")


def main() -> None:
    """Generate and either process or write a static list of stages"""
    args = parse_args()
    logging.basicConfig(
        format="%(levelname)s %(name)s %(asctime)s: %(message)s",
        datefmt='%H:%M:%S',
        level=getattr(logging, {0: "WARNING", 1: "INFO", 2: "DEBUG"}.get(args.verbose, "WARNING")),
    )
    LOG.debug("Python: %s %s", '.'.join(map(str, sys.version_info)), sys.executable)
    LOG.debug("Args: %s", args.__dict__)
    LOG.debug("CWD: %s", os.getcwd())
    env_vars = {key: value for var in args.env for key, value in (var.split("=", 1),)}
    LOG.debug("Variables provided via command: %s", env_vars)
    for key, value in os.environ.items():
        LOG.debug("ENV: %s: %s", key, value)

    if not args.write_file:
        print(f"Read and process {args.input}")

    variables, stages = compile_stage_info(args.input, env_vars, args.no_skip)

    if not args.write_file:
        print("Modified files ($CHANGED_FILES_REL):")
        for file in variables.get('CHANGED_FILES_REL', '').split():
            print(f"  {file}")

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
        print(f"Found {len(stages)} stage commands to run locally")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_locally(stages, args.exitfirst, args.filter_substring, args.verbose))
        loop.close()


if __name__ == "__main__":
    main()
