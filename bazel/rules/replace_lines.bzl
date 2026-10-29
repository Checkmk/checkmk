"""Rule to replace whole lines of a shipped file at build time.

The agent's installation scripts declare their paths as shell defaults, for
example `: "${MK_INSTALLDIR:=""}"`, and its systemd units and xinetd template
name the agent binaries by absolute path. The agent bakery rewrites all of
these per host through its `line_mapping` mechanism. The prebuilt agent
packages have no bakery behind them, so the build rewrites them here instead.

Unlike `replace_string_in_file`, this rule matches whole lines and fails when a
line to replace is not found exactly once. A silent miss would produce an agent
package whose files sit in the single-directory tree while its scripts and
units still point at the classic one.
"""

load("@bazel_skylib//lib:shell.bzl", "shell")

def _replace_lines_impl(ctx):
    src = ctx.file.src
    out = ctx.outputs.out

    verifications = []
    awk_variables = []
    awk_rules = []
    for index, (old_line, new_line) in enumerate(ctx.attr.substitutions.items()):
        verifications.append(
            """found="$(grep -cxF -- {old_line} {src} || true)"
if [ "${{found}}" != "1" ]; then
    echo "{name}: expected exactly one line {old_line}, found ${{found}}" >&2
    exit 1
fi""".format(
                name = ctx.label.name,
                old_line = shell.quote(old_line),
                src = shell.quote(src.path),
            ),
        )
        awk_variables.append("-v old%d=%s" % (index, shell.quote(old_line)))
        awk_variables.append("-v new%d=%s" % (index, shell.quote(new_line)))
        awk_rules.append("$0 == old%d { print new%d; next }" % (index, index))

    ctx.actions.run_shell(
        inputs = [src],
        outputs = [out],
        command = "\n".join(["set -eu"] + verifications + [
            "awk {variables} {program} {src} > {out}".format(
                variables = " ".join(awk_variables),
                program = shell.quote("\n".join(awk_rules + ["{ print }"])),
                src = shell.quote(src.path),
                out = shell.quote(out.path),
            ),
        ]),
        mnemonic = "ReplaceLines",
        progress_message = "Replacing lines in %s" % src.short_path,
    )

replace_lines = rule(
    doc = """Copies `src` to `out`, replacing whole lines.

    Args:
        name: Name of the rule.
        src: The file to rewrite.
        out: Path of the output file, relative to this package.
        substitutions: dict in the form {old line: new line}. Each key must
            match exactly one line of `src`, or the build fails.
    """,
    implementation = _replace_lines_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "src": attr.label(mandatory = True, allow_single_file = True),
        "substitutions": attr.string_dict(mandatory = True, allow_empty = False),
    },
)
