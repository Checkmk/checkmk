load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "basics",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk/base/modes:__pkg__",
        "//non-free/packages/cmk-metric-backend:__pkg__",
        "//non-free/tests/testlib/system/licensing:__pkg__",
        "//omd/packages/Python:__pkg__",
        "//packages/cmk-agent-receiver:__subpackages__",
        "//packages/cmk-licensing:__subpackages__",
    ],
    deps = [
        # NOTE: since this is used in sitecustomize.py, keep the deps to a minimum
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
    ],
)
