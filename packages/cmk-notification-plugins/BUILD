load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-notification-plugins",
    srcs = glob(["cmk/notification_plugins/**/*.py"]),
    data = ["cmk/notification_plugins/py.typed"],
    imports = ["."],
    visibility = [
        "//visibility:public",
    ],
    deps = [
        "//cmk/utils",
        requirement("jinja2"),
        requirement("opsgenie-sdk"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-notification-plugins",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("jinja2"),
        requirement("requests"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-notification-plugins",
    strip_path_prefixes = ["packages/cmk-notification-plugins"],
    version = "1.0.0",
    deps = [
        ":cmk-notification-plugins",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "wheel_pkg",
    whl = "wheel",
)

py_library(
    name = "notification_scripts_lib",
    srcs = glob(["notifications/*.py"]),
    imports = ["."],
    deps = [
        ":cmk-notification-plugins",
    ],
)

pkg_files(
    name = "notification_scripts",
    srcs = glob(["notifications/*.py"]) + ["notifications/mkeventd"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/notifications",
    renames = {
        "notifications/asciimail.py": "asciimail",
        "notifications/cisco_webex_teams.py": "cisco_webex_teams",
        "notifications/ilert.py": "ilert",
        "notifications/mail.py": "mail",
        "notifications/msteams.py": "msteams",
        "notifications/opsgenie_issues.py": "opsgenie_issues",
        "notifications/pagerduty.py": "pagerduty",
        "notifications/pushover.py": "pushover",
        "notifications/signl4.py": "signl4",
        "notifications/slack.py": "slack",
        "notifications/sms.py": "sms",
        "notifications/sms_api.py": "sms_api",
        "notifications/spectrum.py": "spectrum",
        "notifications/victorops.py": "victorops",
    },
)

pkg_files(
    name = "readme",
    srcs = ["notifications/README"],
    prefix = "share/check_mk/notifications",
)

pkg_files(
    name = "templates",
    srcs = glob(["templates/mail/*"]),
    prefix = "share/check_mk/notifications/templates/mail",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":notification_scripts",
        ":readme",
        ":templates",
    ],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
    deps = [":wheel_pkg"],
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-notification-plugins",
    ],
    requirements_in = "requirements.in",
)
