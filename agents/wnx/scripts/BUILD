load("@rules_python//python:defs.bzl", "py_binary")

py_binary(
    name = "check_hashes",
    srcs = ["check_hashes.py"],
    main = "check_hashes.py",
    visibility = ["//visibility:public"],
)

py_binary(
    name = "check_crlf",
    srcs = ["check_crlf.py"],
    main = "check_crlf.py",
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "sign_azure",
    srcs = ["sign_azure.sh"],
    data = [
        "//tests/packaging:signing_roots",
        "@osslsigncode",
        "@psign",
    ],
    env = {
        "SIGN_AZURE_OSSLSIGNCODE": "$(rlocationpath @osslsigncode)",
        "SIGN_AZURE_PSIGN": "$(rlocationpath @psign)",
        "SIGN_AZURE_ROOTS": "$(rlocationpaths //tests/packaging:signing_roots)",
    },
    deps = ["@bazel_tools//tools/bash/runfiles"],
)
