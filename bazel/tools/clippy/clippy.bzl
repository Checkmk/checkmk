"""API for declaring a clippy lint aspect that visits rust_{binary|library|test} rules.

Typical usage:

First, install `rules_rust` into your repository, on at least version 0.67.0: https://bazelbuild.github.io/rules_rust/.
For instance:

```starlark
// MODULE.bazel
bazel_dep(name = "rules_rust", version = "0.67.0")

rust = use_extension("@rules_rust//rust:extensions.bzl", "rust")
rust.toolchain(
    edition = "2021",
    versions = ["1.75.0"],
)
use_repo(rust, "rust_toolchains")

register_toolchains(
    "@rust_toolchains//:all",
)
```

This will install a rust toolchain, which includes rustc and clippy.
Please ignore the `rules_rust` instructions around clippy, as `rules_lint` ignores all `rules_rust` flags.

Next, create a clippy configuration file. We'll assume you've created it in `//:.clippy.toml`.
The file name must be suffixed by either `.clippy.toml` or `clippy.toml`, otherwise clippy will silently ignore it.

Finally, create the linter aspect, typically in `tools/lint/linters.bzl`:

```starlark
load("//bazel/tools/clippy:clippy.bzl", "lint_clippy_aspect")

clippy = lint_clippy_aspect(
    config = Label("//:.clippy.toml"),
    # Any clippy flags as needed like "-DWarnings".
    clippy_flags = ["-Dwarnings"],
)
```

Now your targets will be linted with clippy.
If you wish a target to be excluded from linting, you can give them the `noclippy` tag.
If you wish a clippy lint exception to fail the build, please enable the `--@aspect_rules_lint//lint:fail_on_violation` flag.

Please note that the aspect will propagate to all transitive Rust dependencies of your
`rust_library`, `rust_binary`, and `rust_test` targets.

Please watch issue https://github.com/aspect-build/rules_lint/issues/385 for updates on this behavior.
"""

load("@aspect_rules_lint//lint:defs.bzl", "LintOptionsInfo", "OUTFILE_FORMAT", "filter_srcs", "noop_lint_action", "output_files", "patch_and_output_files", "patcher_attrs", "run_patcher", "should_visit")
load("@rules_rust//rust:defs.bzl", "rust_clippy_action")

_MNEMONIC = "AspectRulesLintClippy"

def _parse_wrapper_output_into_files(ctx, outputs, raw_process_wrapper_wrapper_output):
    arguments = [
        raw_process_wrapper_wrapper_output.path,
        outputs.human.out.path,
    ]
    outs = [
        outputs.human.out,
    ]
    command = """
exit_code=$(head -n 1 $1)
if [ "$exit_code" -eq 0 ]; then
    # clippy exits with 0 (no error) with `-Wwarnings` (`-Dwarnings` is required
    # to treat warnings as errors.  However, we want `fail_on_violation` to fail
    # the build in case of warnings, too.
    # We thus have to explicitly search for warnings in clippy's output message.
    warning_count="$(grep -m1 -oP '\\d+(?= warnings emitted)' "$1")"
    if [ -n "$warning_count" ] && [ "$warning_count" -ne 0 ]; then
        exit_code=1
    fi
fi

output=$(tail -n +2 $1)
if [[ "${output}" != "" ]]; then
    echo "${output}" > $2
else
    touch $2
fi
"""

    if outputs.human.exit_code and outputs.machine.exit_code:
        arguments.append(outputs.human.exit_code.path)
        arguments.append(outputs.machine.exit_code.path)
        outs.append(outputs.human.exit_code)
        outs.append(outputs.machine.exit_code)
        command += """
echo "${exit_code}" > $3
echo "${exit_code}" > $4
echo "${output}" >&2
"""

    ctx.actions.run_shell(
        command = command,
        arguments = arguments,
        inputs = [
            raw_process_wrapper_wrapper_output,
        ],
        outputs = outs,
    )

_CLIPPY_SKIP_TAG = "noclippy"

def _has_skip_tag(rule):
    return _CLIPPY_SKIP_TAG in rule.attr.tags

# buildifier: disable=function-docstring
def _clippy_aspect_impl(target, ctx):
    if not should_visit(ctx.rule, ctx.attr._rule_kinds):
        return []

    clippy_bin = ctx.toolchains[Label("@rules_rust//rust:toolchain_type")].clippy_driver

    files_to_lint = filter_srcs(ctx.rule)

    # Declare outputs with sibling = crate_info.output when available, so they're placed in the same directory
    # structure that rustc expects. This is required because rust_clippy_action sets --out-dir based on
    # crate_info.output and rustc needs to write .d files to that directory
    crate_info = rust_clippy_action.get_clippy_ready_crate_info(target, ctx)
    sibling = crate_info.output if crate_info else None

    patch_file = None
    if ctx.attr._options[LintOptionsInfo].fix:
        outputs, info = patch_and_output_files(_MNEMONIC, target, ctx, sibling)
        patch_file = getattr(outputs, "patch", None)
    else:
        outputs, info = output_files(_MNEMONIC, target, ctx, sibling)

    if len(files_to_lint) == 0 or not crate_info or _has_skip_tag(ctx.rule):
        noop_lint_action(ctx, outputs)
        return [info]

    clippy_flags = [
        # If we don't pass any clippy options, rules_rust will (rightly) default to -Dwarnings, which turns all warnings into errors.
        # They do this to force Bazel to re-run targets on failures.
        # However, we don't need to do that because we keep track of output files and exit codes separately.
        "-Wwarnings",
    ] + ctx.attr._clippy_flags + ctx.attr._args

    raw_output = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = _MNEMONIC, suffix = "raw_process_wrapper_wrapper_output_human"), sibling = sibling)
    raw_rustc_json_diagnostics = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = _MNEMONIC, suffix = "rustc_json_diagnostics"), sibling = sibling)
    raw_output = ctx.actions.declare_file(OUTFILE_FORMAT.format(label = target.label.name, mnemonic = _MNEMONIC, suffix = "raw_process_wrapper_wrapper_output_human"), sibling = sibling)

    rust_clippy_action.action(
        ctx,
        clippy_executable = clippy_bin,
        process_wrapper = ctx.executable._process_wrapper_wrapper,
        crate_info = crate_info,
        config = ctx.file._config_file,
        output = raw_output,
        cap_at_warnings = False,
        extra_clippy_flags = clippy_flags,
        clippy_diagnostics_file = raw_rustc_json_diagnostics,
    )

    _parse_wrapper_output_into_files(ctx, outputs, raw_output)
    _parse_to_sarif_action(ctx, raw_rustc_json_diagnostics, outputs.machine.out)

    if patch_file != None:
        _run_patcher(ctx, files_to_lint, raw_rustc_json_diagnostics, patch_file)

    return [info]

def _run_patcher(ctx, srcs, rustc_diagnostics_file, patch_file):
    args = [
        "patch",
        # This path is relative to the execroot, we must relativize it to the bindir.
        "../../../" + rustc_diagnostics_file.path,
    ]

    # Use ctx.actions.symlink instead of copy_files_to_bin_actions so that the
    # aspect creates the same action type (SymlinkAction) as rules_rust does when
    # a target has generated inputs. rules_rust symlinks all source files to the
    # bin directory in that case, and Bazel resolves shareable action conflicts
    # only when the action keys match — which requires identical action types.
    # See: https://github.com/bazelbuild/rules_rust/blob/74bd3d15f33c6133c84bf4348225cbc7ac206f51/rust/private/utils.bzl#L857
    srcs_inputs = []
    for src in srcs:
        if src.is_source:
            # Strip the package prefix to get the path relative to the package,
            # so declare_file places the output at bazel-out/.../bin/<package>/<relative>.
            package_prefix = ctx.label.package + "/"
            relative_path = src.short_path[len(package_prefix):] if src.short_path.startswith(package_prefix) else src.short_path
            bin_file = ctx.actions.declare_file(relative_path)
            ctx.actions.symlink(output = bin_file, target_file = src)
            srcs_inputs.append(bin_file)
        else:
            srcs_inputs.append(src)

    run_patcher(
        ctx,
        ctx.executable,
        inputs = [rustc_diagnostics_file] + srcs_inputs,
        args = args,
        tools = [ctx.executable._rustc_diagnostic_parser],
        files_to_diff = [s.path for s in srcs],
        patch_out = patch_file,
        patch_cfg_env = {"BAZEL_BINDIR": ctx.bin_dir.path},
        env = {},
        mnemonic = _MNEMONIC,
        progress_message = "Applying Clippy fixes to %{label}",
    )

def _parse_to_sarif_action(ctx, rustc_diagnostics_file, sarif_output):
    args = [
        "sarif",
        rustc_diagnostics_file.path,
        sarif_output.path,
    ]

    ctx.actions.run(
        executable = ctx.executable._rustc_diagnostic_parser,
        arguments = args,
        inputs = [rustc_diagnostics_file],
        outputs = [sarif_output],
        # Must be set for js_binary to run.
        # Ref: https://github.com/aspect-build/rules_js/tree/dbb5af0d2a9a2bb50e4cf4a96dbc582b27567155?tab=readme-ov-file#running-nodejs-programs
        env = {
            "BAZEL_BINDIR": ".",
        },
    )

DEFAULT_RULE_KINDS = ["rust_binary", "rust_library", "rust_shared_library", "rust_test"]

def lint_clippy_aspect(config, rule_kinds = DEFAULT_RULE_KINDS, clippy_flags = [], args = []):
    """A factory function to create a linter aspect.

    The Clippy binary will be read from the Rust toolchain.

    Args:
        config (File): Label of the desired Clippy configuration file to use. Reference: https://doc.rust-lang.org/clippy/configuration.html
        rule_kinds (List[str]): List of rule kinds to lint. Defaults to {default_rule_kinds}.
        clippy_flags (List[str]): Extra clippy/rustc lint flags (e.g. `-Dwarnings`, `-Aclippy::style`).
        args (List[str]): Additional options to pass to Clippy.
    """.format(default_rule_kinds = DEFAULT_RULE_KINDS)
    attrs = {
        "_args": attr.string_list(
            default = args,
        ),
        "_clippy_flags": attr.string_list(
            default = clippy_flags,
        ),
        "_config_file": attr.label(
            default = config,
            allow_single_file = True,
        ),
        "_options": attr.label(
            default = "@aspect_rules_lint//lint:options",
            providers = [LintOptionsInfo],
        ),
        "_process_wrapper_wrapper": attr.label(
            doc = "A wrapper around the rules_rust process wrapper. See //bazel/tools/clippy:process_wrapper_wrapper for motivation and documentation.",
            default = Label(":process_wrapper_wrapper"),
            executable = True,
            cfg = "exec",
        ),
        "_rule_kinds": attr.string_list(
            default = rule_kinds,
        ),
        "_rustc_diagnostic_parser": attr.label(
            doc = """A binary that can convert JSON rustc diagnostics into SARIF.

Note that rustc diagnostics are different from cargo diagnostics, which is what common rust implementations like sarif-rs use.
In particular, cargo diagnostics _may contain_ rustc diagnostics, but they don't have to.

References:
- Rustc diagnostic format: https://doc.rust-lang.org/beta/rustc/json.html#diagnostics
""",
            default = Label(":cli"),
            executable = True,
            cfg = "exec",
        ),
        "_rustc_sarif_parser": attr.label(
            doc = """A binary that can convert JSON rustc diagnostics into SARIF.

Note that rustc diagnostics are different from cargo diagnostics, which is what common rust implementations like sarif-rs use.
In particular, cargo diagnostics _may contain_ rustc diagnostics, but they don't have to.

References:
- Rustc diagnostic format: https://doc.rust-lang.org/beta/rustc/json.html#diagnostics
""",
            default = Label(":cli"),
            executable = True,
            cfg = "exec",
        ),
    }
    return aspect(
        fragments = ["cpp"],
        attr_aspects = ["deps"],
        implementation = _clippy_aspect_impl,
        attrs = patcher_attrs | attrs,
        toolchains =
            [
                Label("@rules_rust//rust:toolchain_type"),
                "@bazel_tools//tools/cpp:toolchain_type",
            ],
    )
