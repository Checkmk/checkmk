load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "basics",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = [
        "//cmk/gui_plugins/internal:__pkg__",
        "//cmk/plugins/checkmk/cli:__subpackages__",
        "//non-free/packages/cmk-ai-control-plane:__pkg__",
        "//non-free/packages/cmk-data-backend:__pkg__",
        "//non-free/tests/testlib/common/licensing:__pkg__",
        "//non-free/tests/testlib/system:__pkg__",
        "//non-free/tests/testlib/system/licensing:__pkg__",
        "//non-free/tests/testlib/unit:__pkg__",
        "//omd/packages/Python:__pkg__",
        "//packages/cmk-agent-receiver:__subpackages__",
        "//packages/cmk-licensing:__subpackages__",
    ],
    deps = [
        # NOTE: since this is used in sitecustomize.py, keep the deps to a minimum.
        # Enforced by //omd/packages/Python:sitecustomize_deps_test.
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
    ],
)
