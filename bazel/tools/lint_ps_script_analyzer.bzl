"""API for declaring a PSScriptAnalyzer lint aspect that visits filegroups
tagged lint-with-psscriptanalyzer (or any rule kinds provided by the caller).

Vendored from https://github.com/aspect-build/rules_lint/pull/850. When the upstream PR merges,
swap the load() path in bazel/tools/aspects.bzl to
@aspect_rules_lint//lint:ps_script_analyzer.bzl and delete this file plus
ps_script_analyzer_wrapper.ps1.
"""

load(
    "@aspect_rules_lint//lint:defs.bzl",
    "LintOptionsInfo",
    "filter_srcs",
    "noop_lint_action",
    "output_files",
    "should_visit",
)

_MNEMONIC = "AspectRulesLintPSScriptAnalyzer"

_PS_EXTENSIONS = (".ps1", ".psm1")

def _ps_files(files):
    return [f for f in files if f.basename.endswith(_PS_EXTENSIONS)]

def _ps_script_analyzer_aspect_impl(target, ctx):
    if not should_visit(ctx.rule, ctx.attr._rule_kinds, ctx.attr._filegroup_tags):
        return []

    files_to_lint = _ps_files(filter_srcs(ctx.rule))
    outputs, info = output_files(_MNEMONIC, target, ctx)

    if len(files_to_lint) == 0:
        noop_lint_action(ctx, outputs)
        return [info]

    wrapper = ctx.file._wrapper
    pwsh = ctx.file._pwsh
    pssa_files = ctx.files._psscriptanalyzer
    sarif_files = ctx.files._converttosarif

    pssa_matches = [f for f in pssa_files if f.basename == "PSScriptAnalyzer.psd1"]
    if not pssa_matches:
        fail("PSScriptAnalyzer.psd1 not found in the psscriptanalyzer filegroup. " +
             "Ensure the http_archive for @psscriptanalyzer points to a PSScriptAnalyzer nupkg.")
    pssa_psd1 = pssa_matches[0]

    sarif_matches = [f for f in sarif_files if f.basename == "ConvertToSARIF.psd1"]
    if not sarif_matches:
        fail("ConvertToSARIF.psd1 not found in the converttosarif filegroup. " +
             "Ensure the http_archive for @converttosarif points to a ConvertToSARIF nupkg.")
    sarif_psd1 = sarif_matches[0]

    args = ctx.actions.args()
    args.add_all(files_to_lint)

    # Use $PWD/ to make psd1 paths absolute: Import-Module doesn't recognise
    # relative paths that don't start with ./ or / (e.g. "external/repo/foo.psd1"
    # is treated as a module name search, not a file path).
    cmd = (
        "{pwsh} -NonInteractive -File {wrapper}" +
        " -PssaPsd1 $PWD/{pssa} -SarifPsd1 $PWD/{sarif}" +
        " -OutFile {outfile} -SarifFile {sariffile}"
    ).format(
        pwsh = pwsh.path,
        wrapper = wrapper.path,
        pssa = pssa_psd1.path,
        sarif = sarif_psd1.path,
        outfile = outputs.human.out.path,
        sariffile = outputs.machine.out.path,
    )

    action_outputs = [outputs.human.out, outputs.machine.out]

    if outputs.human.exit_code:
        cmd += " -HumanExitCodeFile {hec} -MachineExitCodeFile {mec}".format(
            hec = outputs.human.exit_code.path,
            mec = outputs.machine.exit_code.path,
        )
        action_outputs += [outputs.human.exit_code, outputs.machine.exit_code]

    if ctx.file._config_file:
        cmd += " -Settings {settings}".format(settings = ctx.file._config_file.path)

    cmd += " $@"

    action_inputs = files_to_lint + pssa_files + sarif_files + [wrapper]
    if ctx.file._config_file:
        action_inputs = action_inputs + [ctx.file._config_file]

    ctx.actions.run_shell(
        inputs = action_inputs,
        outputs = action_outputs,
        arguments = [args],
        command = cmd,
        tools = [pwsh],
        mnemonic = _MNEMONIC,
        progress_message = "Linting %{label} with PSScriptAnalyzer",
    )

    return [info]

def lint_ps_script_analyzer_aspect(
        binary,
        psscriptanalyzer,
        converttosarif,
        config = None,
        rule_kinds = [],
        filegroup_tags = ["lint-with-psscriptanalyzer"]):
    """A factory function to create a linter aspect for PSScriptAnalyzer.

    Args:
        binary: label of the pwsh executable (e.g. Label("@pwsh//:pwsh"))
        psscriptanalyzer: label of the PSScriptAnalyzer filegroup from http_archive
        converttosarif: label of the ConvertToSARIF filegroup from http_archive
        config: optional label of a .psd1 settings file
        rule_kinds: Bazel rule kinds to lint (default: none, use filegroup_tags instead)
        filegroup_tags: filegroup tags that opt targets into linting
    """
    return aspect(
        implementation = _ps_script_analyzer_aspect_impl,
        attrs = {
            "_config_file": attr.label(
                default = config,
                allow_single_file = True,
            ),
            "_converttosarif": attr.label(
                default = converttosarif,
                allow_files = True,
            ),
            "_filegroup_tags": attr.string_list(
                default = filegroup_tags,
            ),
            "_options": attr.label(
                default = "@aspect_rules_lint//lint:options",
                providers = [LintOptionsInfo],
            ),
            "_psscriptanalyzer": attr.label(
                default = psscriptanalyzer,
                allow_files = True,
            ),
            "_pwsh": attr.label(
                default = binary,
                allow_single_file = True,
                cfg = "exec",
            ),
            "_rule_kinds": attr.string_list(
                default = rule_kinds,
            ),
            "_wrapper": attr.label(
                default = "//bazel/tools:ps_script_analyzer_wrapper.ps1",
                allow_single_file = True,
            ),
        },
        toolchains = [],
    )
