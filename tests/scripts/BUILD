load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "scripts",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../.."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("docker"),
        requirement("requests"),
        requirement("jinja2"),
        "//tests/testlib",
        "//tests/testlib/pytest_helpers",
    ],
)

sh_library(
    name = "tests_sh",
    srcs = [
        "find_modified_lock_files",
        "setup_openldap.sh",
        "setup_postfix.sh",
        "teardown_openldap.sh",
        "teardown_postfix.sh",
        "verify_test_python_files.sh",
    ],
)
