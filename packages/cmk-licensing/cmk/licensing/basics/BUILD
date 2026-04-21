load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "basics",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//omd/packages/Python:__pkg__",
        "//packages/cmk-licensing:__subpackages__",
    ],
    deps = [
        # NOTE: since this is used in sitecustomize.py, keep the deps to a minimum
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
    ],
)
