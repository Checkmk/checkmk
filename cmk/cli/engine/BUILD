load("@aspect_rules_py//py:defs.bzl", "py_library")

# The engine of the "cmk" command line: it declares the general options, parses
# the command line, discovers the CLICommand plug-ins and calls the selected
# one. The commands themselves are plug-ins and live in cmk/plugins/<family>/cli/.
#
# NOTE: `cmk.cli` is a PEP 420 namespace package -- never add a cmk/cli/__init__.py.
# The `internal` portion (the plug-in API) is contributed by cmk-plugin-apis.
py_library(
    name = "engine",
    srcs = [
        "arguments.py",
        "call.py",
        "modes.py",
    ],
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/base:base-app",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-trace",
    ],
)

# The entry point. Separate from :engine because it assembles the application,
# which depends on the commands, which depend on :engine.
py_library(
    name = "main",
    srcs = ["main.py"],
    imports = ["../../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/base:__subpackages__",
    ],
    deps = [
        ":engine",
        "//cmk/base:app",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-profiling:backend",
        "//packages/cmk-trace",
    ],
)
