load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

py_library(
    name = "veeam",
    srcs = glob(["**/*.py"]),
    data = glob([
        "agents/*",
        "checkman/*",
        "libexec/*",
    ]) + ["py.typed"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:bakery",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        requirement("pydantic"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

filegroup(
    name = "agents",
    srcs = glob(["agents/**/*"]),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

# Referenced by name from agents/wnx/install/Product.wxs.
exports_files(
    ["agents/veeam_backup_status.ps1"],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = ["agents/veeam_backup_status.ps1"],
    tags = ["lint-with-psscriptanalyzer"],
)

filegroup(
    name = "checkman",
    srcs = glob(["checkman/**/*"]),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

sh_library(
    name = "libexec",
    srcs = glob(["libexec/*"]),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)
