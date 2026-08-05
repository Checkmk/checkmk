load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "singlesite",
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
    data = glob(
        include = ["**/test_plugins/**"],
        exclude = ["**/*.py"],
    ),
    imports = ["../../.."],
    deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pysaml2"),
        requirement("matplotlib"),
        requirement("requests"),
        requirement("pyyaml"),
        requirement("clickhouse_connect"),
        requirement("cryptography"),
        requirement("python-dateutil"),
        requirement("types-python-dateutil"),
        requirement("pysnmp"),
        requirement("psutil"),
        requirement("semver"),
        requirement("polyfactory"),
        requirement("psycopg"),
        requirement("protobuf"),
        requirement("pyopenssl"),
        requirement("beautifulsoup4"),
        "//cmk/post_rename_site",
        "//cmk/utils:msi_patch",
        "//cmk/utils:redis",
        "//packages/cmk-agent-receiver",
        "//tests:scripts",
        "//tests/system:pkg_marker",
        "//tests/testlib",
        "//tests/testlib/common:utils",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//non-free/packages/cmk-liveproxyd",
            "//non-free/packages/cmk-telemetry:plugins-custom-query",
            "//non-free/tests/testlib/system:metric_backend",
            "//non-free/tests/testlib/system:opentelemetry",
            "//non-free/tests/testlib/system/cloud",
            "//non-free/tests/testlib/system/licensing",
        ],
        "//:gpl_repo": [],
    }),
)
