load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "agents",
    srcs = [
        "apache_status.py",
        "isc_dhcpd.py",
    ],
    visibility = [
        "//cmk/plugins:__subpackages__",
        "//tests:__subpackages__",
    ],
)

exports_files(
    [
        "iis_app_pool_state.ps1",
        "mcafee_av_client.bat",
        "win_dmidecode.bat",
    ],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = ["iis_app_pool_state.ps1"],
    tags = ["lint-with-psscriptanalyzer"],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = [
        "kaspersky_av",
        "lnx_quota",
        "mk_nfsiostat",
        "mk_zypper",
    ],
)

exports_files(
    ["kaspersky_av"],
    visibility = ["//tests/unit-shell/agents:__pkg__"],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
