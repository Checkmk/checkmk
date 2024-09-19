load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

py_library(
    name = "cmk-rulesets",
    srcs = [
        "cmk/rulesets/__init__.py",
        "cmk/rulesets/v1/__init__.py",
        "cmk/rulesets/v1/_localize.py",
        "cmk/rulesets/v1/form_specs/__init__.py",
        "cmk/rulesets/v1/form_specs/_base.py",
        "cmk/rulesets/v1/form_specs/_basic.py",
        "cmk/rulesets/v1/form_specs/_composed.py",
        "cmk/rulesets/v1/form_specs/_levels.py",
        "cmk/rulesets/v1/form_specs/_migrations.py",
        "cmk/rulesets/v1/form_specs/_preconfigured.py",
        "cmk/rulesets/v1/form_specs/validators.py",
        "cmk/rulesets/v1/rule_specs.py",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-rulesets",
    strip_path_prefixes = ["packages/cmk-rulesets"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-rulesets",
    ],
)

package_wheel(wheel_target = "wheel")
