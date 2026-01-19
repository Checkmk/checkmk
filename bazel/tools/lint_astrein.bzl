"""Astrein linter aspect for aspect_rules_lint framework"""

_MNEMONIC = "AspectRulesLintAstrein"

# Taken from https://github.com/aspect-build/rules_lint/blob/main/lint/private/lint_aspect.bzl
# to avoid imports from private modules
def should_visit(rule, allow_kinds, allow_filegroup_tags = []):
    """Determine whether a rule is meant to be visited by a linter aspect

    A target with the "no-lint" tag will not be visited.

    Args:
        rule: a [rules_attributes](https://bazel.build/rules/lib/builtins/rule_attributes.html) object
        allow_kinds (list of string): return true if the rule's kind is in the list
        allow_filegroup_tags (list of string): return true if the rule is a filegroup and has a tag in this list

    Returns:
        whether to apply the aspect on this rule
    """
    if "no-lint" in rule.attr.tags:
        return False

    if rule.kind in allow_kinds:
        return True
    if rule.kind == "filegroup":
        for allow_tag in allow_filegroup_tags:
            if allow_tag in rule.attr.tags:
                return True
    return False

# Taken from https://github.com/aspect-build/rules_lint/blob/main/lint/private/lint_aspect.bzl
# to avoid imports from private modules
def filter_srcs(rule):
    if "lint-genfiles" in rule.attr.tags:
        return rule.files.srcs
    else:
        return [s for s in rule.files.srcs if s.is_source and s.owner.workspace_name == ""]

OUTFILE_FORMAT = "{label}.{mnemonic}.{suffix}"

# Taken from https://github.com/aspect-build/rules_lint/blob/main/lint/private/lint_aspect.bzl
# to avoid imports from private modules
def output_files(mnemonic, target, ctx):
    """Declare linter output files.

    Args:
        mnemonic: used as part of the filename
        target: the target being visited by a linter aspect
        ctx: the aspect context

    Returns:
        tuple of struct() of output files, and the OutputGroupInfo provider that the rule should return
    """
    human_out = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = mnemonic, suffix = "out"))

    # NB: named ".report" as there are existing callers depending on that
    machine_out = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = mnemonic, suffix = "report"))

    # The exit codes should instead be provided as action outputs so the build succeeds.
    # Downstream tooling like `aspect lint` will be responsible for reading the exit codes
    # and interpreting them.
    human_exit_code = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = mnemonic, suffix = "out.exit_code"))
    machine_exit_code = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = mnemonic, suffix = "report.exit_code"))

    human_outputs = [f for f in [human_out, human_exit_code] if f]
    machine_outputs = [f for f in [machine_out, machine_exit_code] if f]
    return struct(
        human = struct(
            out = human_out,
            exit_code = human_exit_code,
        ),
        machine = struct(
            out = machine_out,
            exit_code = machine_exit_code,
        ),
    ), OutputGroupInfo(
        rules_lint_human = depset(human_outputs),
        rules_lint_machine = depset(machine_outputs),
        # Legacy name used by existing callers.
        # TODO(2.0): remove
        rules_lint_report = depset(machine_outputs),
        # Always cause the action to execute, even if the output isn't requested
        _validation = depset([human_out]),
    )

# Inspired by https://github.com/aspect-build/rules_lint/blob/main/lint/private/lint_aspect.bzl
def noop_lint_action(ctx, outputs):
    """Generates an action that creates empty outputs when no files need linting.

    Args:
        ctx: Bazel context
        outputs: Output files struct
    """
    ctx.actions.write(
        output = outputs.human.out,
        content = "",
    )
    if outputs.human.exit_code:
        ctx.actions.write(
            output = outputs.human.exit_code,
            content = "0\n",
        )
    ctx.actions.write(
        output = outputs.machine.out,
        content = "",
    )
    if outputs.machine.exit_code:
        ctx.actions.write(
            output = outputs.machine.exit_code,
            content = "0\n",
        )

def astrein_action(ctx, executable, srcs, stdout, exit_code, format, astrein_runfiles):
    """Run astrein linter on source files.

    Args:
        ctx: Bazel context
        executable: The astrein CLI executable
        srcs: Source files to lint
        stdout: Output file for lint results
        exit_code: Optional file to capture exit code (None if fail_on_violation is true)
        format: Output format ("gcc" or "sarif")
        astrein_runfiles: Runfiles of the astrein binary (includes config files)
    """
    if exit_code:
        outputs = [stdout, exit_code]
        command = "{astrein} --checker all --format {format} --output {out} {srcs}; echo $? > {exit_code}".format(
            astrein = executable.path,
            format = format,
            out = stdout.path,
            exit_code = exit_code.path,
            srcs = " ".join([f.path for f in srcs]),
        )
    else:
        outputs = [stdout]
        command = "{astrein} --checker all --format {format} --output {out} {srcs}".format(
            astrein = executable.path,
            format = format,
            out = stdout.path,
            srcs = " ".join([f.path for f in srcs]),
        )

    # Include astrein's runfiles as inputs so Bazel invalidates the cache when they change
    # (e.g. layer checker config)
    all_inputs = depset(direct = srcs, transitive = [astrein_runfiles])

    ctx.actions.run_shell(
        command = command,
        inputs = all_inputs,
        outputs = outputs,
        tools = [executable],
        mnemonic = _MNEMONIC,
        progress_message = "Linting %{label} with astrein (" + format + ")",
    )

def _astrein_aspect_impl(target, ctx):
    if "no-astrein" in ctx.rule.attr.tags:
        return []

    if not should_visit(ctx.rule, ctx.attr._rule_kinds, ctx.attr._filegroup_tags):
        return []

    if not hasattr(ctx.rule.attr, "srcs"):
        return []

    files_to_lint = filter_srcs(ctx.rule)
    py_files = [f for f in files_to_lint if f.extension == "py"]

    outputs, info = output_files(_MNEMONIC, target, ctx)

    if not py_files:
        noop_lint_action(ctx, outputs)
        return [info]

    astrein_runfiles = ctx.attr._astrein_cli[DefaultInfo].default_runfiles.files

    astrein_action(
        ctx,
        ctx.executable._astrein_cli,
        py_files,
        outputs.human.out,
        outputs.human.exit_code,
        "gcc",
        astrein_runfiles,
    )

    astrein_action(
        ctx,
        ctx.executable._astrein_cli,
        py_files,
        outputs.machine.out,
        outputs.machine.exit_code,
        "sarif",
        astrein_runfiles,
    )

    return [info]

def lint_astrein_aspect(binary, rule_kinds = ["py_binary", "py_library", "py_test"], filegroup_tags = ["python", "lint-with-astrein"]):
    return aspect(
        implementation = _astrein_aspect_impl,
        attr_aspects = ["deps"],
        attrs = {
            "_astrein_cli": attr.label(
                default = binary,
                executable = True,
                cfg = "exec",
            ),
            "_filegroup_tags": attr.string_list(
                default = filegroup_tags,
            ),
            "_options": attr.label(
                default = "@aspect_rules_lint//lint:options",
            ),
            "_rule_kinds": attr.string_list(
                default = rule_kinds,
            ),
        },
    )
