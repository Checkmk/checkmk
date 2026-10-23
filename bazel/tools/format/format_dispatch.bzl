"""Single-process driver for the rules_lint formatters.

rules_lint's `format_multirun` runs one wrapper process per language. Each wrapper
initialises the Bash runfiles library twice and scans the arguments with find(1)
before discovering that it has nothing to do, which for a handful of files costs
~1.4s of CPU across 14 processes plus a Python driver. `format_dispatch` produces
the same pair of targets from one shell script (format_dispatch.sh) that sources
rules_lint's format.sh once and runs its per-language routine in forked subshells.

format.sh formats the dialects of JavaScript (JSON, TypeScript, Vue, ...) and CSS
(Less, SCSS) one after the other, in the process of the base language. Here every
dialect is a language of its own and runs in parallel with the others, except for
the languages whose file patterns overlap.
"""

load("@aspect_rules_lint//format:formatter_binary.bzl", "CHECK_FLAGS", "FIX_FLAGS", "TOOLS", "to_attribute_name")
load("@rules_shell//shell:sh_binary.bzl", "sh_binary")

_FORMAT_SH = Label("@aspect_rules_lint//format/private:format.sh")
_LANGUAGES = {to_attribute_name(language): language for language in TOOLS}

# The dialects that format.sh formats with the tool of the base language.
_DIALECTS = {
    "CSS": ["Less", "SCSS"],
    "JavaScript": ["JSON", "JSON5", "JSON with Comments", "TSX", "TypeScript", "Vue"],
}

# Languages whose file patterns overlap: C and C++ both claim *.h, JSON and JSON
# with Comments both claim tsconfig.json and the like. The languages of a group
# share a slot, i.e. run one after the other, so that no file is rewritten by two
# formatters at the same time.
_SHARED_SLOTS = [
    ["C", "C++"],
    ["JSON", "JSON with Comments"],
]
_SLOT = {language: group[0] for group in _SHARED_SLOTS for language in group}

def _rlocation_path(ctx, file):
    if file.short_path.startswith("../"):
        return file.short_path[3:]
    return ctx.workspace_name + "/" + file.short_path

def _format_table_impl(ctx):
    flags = CHECK_FLAGS if ctx.attr.mode == "check" else FIX_FLAGS
    lines = []
    for language, tool in ctx.attr.tools.items():
        executable = tool[DefaultInfo].files_to_run.executable
        if executable == None:
            fail("{} is not executable".format(tool.label))
        lines.extend([
            "|".join([_SLOT.get(dialect, dialect), dialect, _rlocation_path(ctx, executable), flags[TOOLS[language]]])
            for dialect in [language] + _DIALECTS.get(language, [])
        ])
    table = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.write(table, "".join([line + "\n" for line in sorted(lines)]))
    return [DefaultInfo(files = depset([table]))]

_format_table = rule(
    implementation = _format_table_impl,
    attrs = {
        "mode": attr.string(mandatory = True, values = ["check", "fix"]),
        "tools": attr.string_keyed_label_dict(mandatory = True),
    },
    doc = "One `<slot>|<language>|<tool runfiles path>|<flags>` line per language and dialect, read by format_dispatch.sh.",
)

def format_dispatch(name, languages, fix_target, visibility):
    """Formatter binaries `<name>` (fixes in place) and `<name>.check` (verifies only).

    Both take paths as arguments and default to every file git knows about.

    Args:
        name: name of the fixing target; the checking one is `<name>.check`
        languages: language attribute -> formatter binary, with the attribute names of
            rules_lint's format_multirun (`python`, `cc`, `html_jinja`, ...)
        fix_target: label printed in the hint when a check fails
        visibility: visibility of both targets
    """
    unknown = [language for language in languages if language not in _LANGUAGES]
    if unknown:
        fail("unknown languages {}, expected some of {}".format(unknown, sorted(_LANGUAGES)))
    tools = {_LANGUAGES[attribute]: tool for attribute, tool in languages.items()}
    for mode, target in [("fix", name), ("check", name + ".check")]:
        table = target + ".langs"
        _format_table(
            name = table,
            mode = mode,
            tools = tools,
        )
        sh_binary(
            name = target,
            srcs = [Label(":format_dispatch.sh")],
            data = [table, _FORMAT_SH] + {tool: None for tool in tools.values()}.keys(),
            env = {
                "FORMAT_CACHE": ".format_cache/{}/{}".format(native.package_name(), target),
                "FORMAT_FIX_TARGET": fix_target,
                "FORMAT_LANGS": "$(rlocationpath :{})".format(table),
                "FORMAT_MODE": mode,
                "FORMAT_SH": "$(rlocationpath {})".format(_FORMAT_SH),
            },
            visibility = visibility,
            deps = ["@bazel_tools//tools/bash/runfiles"],
        )
