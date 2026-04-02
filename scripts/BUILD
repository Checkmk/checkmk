load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(["requirements.in"])

sh_binary(
    name = "in_bazel",
    srcs = ["in_bazel.sh"],
)

sh_binary(
    # target only for linters, call the script directly
    name = "lint",
    srcs = ["lint.sh"],
)

py_binary(
    name = "sarif_preparse",
    srcs = ["sarif_preparse.py"],
    main = "sarif_preparse.py",
    tags = ["manual"],
    deps = [requirement("sarif-tools")],
)

sh_library(
    name = "scripts_sh",
    srcs = [
        "check-cmk-namespace",
        "check-current-commit",
        "check-licence",
        "check-qa-test-data",
        "create_cognito_config_cloud.sh",
        "fake-artifacts",
        "find-python-files",
        "find-shell-files",
        "lib-precommit",
        "run-doctests",
        "run-groovy-lint",
        "run-in-docker.sh",
        "run-mypy",
        "run-unittests",
        "run-uvenv",
    ],
)

py_binary(
    name = "decent_output",
    srcs = ["decent_output.py"],
    main = "decent_output.py",
    visibility = ["//visibility:public"],
)

py_library(
    name = "scripts_py",
    srcs = [
        "prune_compilation_db.py",
        "update_python_libs.py",
    ],
    deps = [requirement("sarif-tools")],
)
