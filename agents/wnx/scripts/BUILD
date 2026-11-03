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

filegroup(
    name = "powershell_scripts",
    srcs = [
        "sign_code_azure.ps1",
        "tools/findagentmsi.ps1",
    ],
    tags = ["lint-with-psscriptanalyzer"],
)
