load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "unit_test_coverage",
    srcs = glob(["*.py"]),
    imports = ["../../.."],
    deps = [
        requirement("psycopg"),
    ],
)

sh_library(
    name = "code_coverage_sh",
    srcs = ["code_coverage.sh"],
)
