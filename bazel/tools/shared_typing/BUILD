load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load(
    "@npm//bazel/tools:json-schema-to-typescript/package_json.bzl",
    json2ts_bin = "bin",
)
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files(
    ["requirements.in"],
    visibility = ["//packages:__pkg__"],
)

py_library(
    name = "formatter",
    srcs = [
        "utils/__init__.py",
        "utils/format.py",
        "utils/postprocess.py",
    ],
    imports = ["."],
    deps = [
        requirement("black"),
        requirement("datamodel_code_generator"),
        requirement("libcst"),
    ],
)

py_console_script_binary(
    name = "datamodel_codegen",
    pkg = requirement("datamodel-code-generator"),
    script = "datamodel-codegen",
    tags = ["no-mypy"],
    visibility = ["//packages/cmk-shared-typing:__pkg__"],
    deps = [":formatter"],
)

json2ts_bin.json2ts_binary(
    name = "json2ts",
    visibility = ["//packages/cmk-shared-typing:__pkg__"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/*.py"]),
    deps = [
        ":formatter",
        requirement("datamodel_code_generator"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":datamodel_codegen",
        ":formatter",
    ],
    requirements_in = "requirements.in",
)
