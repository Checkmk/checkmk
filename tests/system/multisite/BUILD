load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "multisite",
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
        requirement("clickhouse_connect"),
        requirement("pytest"),
        requirement("cryptography"),
        requirement("lxml"),
        requirement("pysaml2"),
        requirement("python-dateutil"),
        requirement("requests"),
        requirement("opentelemetry-instrumentation-requests"),
        "//cmk/gui/job_scheduler",
        "//packages/cmk-wsgi",
        "//tests:scripts",
        "//tests/system:pkg_marker",
        "//tests/testlib",
        "//tests/testlib/common:utils",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//non-free/packages/cmk-otel-collector:testlib",
            "//non-free/packages/cmk-update-agent:cmk-update-agent-py",
            "//non-free/tests/testlib/system:metric_backend",
            "//non-free/tests/testlib/system:opentelemetry",
            "//non-free/tests/testlib/system/cloud",
        ],
        "//:gpl_repo": [],
    }),
)
