load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "gui",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = ["../../.."],
    deps = [
        "//packages/cmk-plugins/cmk/plugins/aws",
        "//packages/cmk-plugins/cmk/plugins/azure_v2",
        "//packages/cmk-plugins/cmk/plugins/gcp",
        requirement("playwright"),
        requirement("pytest"),
        requirement("requests"),
        requirement("faker"),
        requirement("pyyaml"),
        requirement("pytest_playwright"),
        requirement("clickhouse_connect"),
        "//tests/system:pkg_marker",
        "//tests/testlib/common",
        "//tests/testlib/pytest_helpers",
        "//tests/testlib/system",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//cmk/gui/nonfree/pro",
            "//non-free/tests/testlib/system:data_backend",
            "//non-free/tests/testlib/system/cloud",
            "//non-free/tests/testlib/system/licensing",
            "//packages/cmk-wsgi",
        ],
        "//:gpl_repo": [],
    }),
)
