load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

# Sign all PowerShell scripts in the current directory.
# `build bazel //agents/windows/plugins:all`
#
# We are using make variables, $, and $@ because we have no correct labels

filegroup(
    name = "plugins",
    srcs = glob(
        ["**"],
        exclude = [
            "BUILD",
            "reference/**",
            "scripts/**",
            ".gitattributes",
            ".gitignore",
            "**/OWNERS",
            ".f12",
        ],
    ),
    tags = ["lint-with-psscriptanalyzer"],
    visibility = ["//visibility:public"],
)

# May contain local file target labels, or cross package labels
# from migrated bakery plugins under cmk/plugins/<family>/
# In the latter case, the file target must be exposed to this package.
TO_SIGN_SCRIPTS = [
    "arcserve_backup.ps1",
    "citrix_farm.ps1",
    "citrix_licenses.ps1",
    "citrix_xenapp.ps1",
    "//cmk/plugins/hyperv/agents:hyperv_vms_guestinfos.ps1",
    "//cmk/plugins/hyperv/agents:hyperv_vms.ps1",
    "//cmk/plugins/collection/agents:iis_app_pool_state.ps1",
    "kaspersky_av_client.ps1",
    "mk_msoffice.ps1",
    "mk_mysql.ps1",
    "mk_oracle.ps1",
    "//cmk/plugins/msexch/agents:msexch_dag.ps1",
    "//cmk/plugins/msexch/agents:msexch_database.ps1",
    "//cmk/plugins/nvidia/agents:nvidia_smi.ps1",
    "rds_licenses.ps1",
    "sansymphony.ps1",
    "//cmk/plugins/veeam/agents:veeam_backup_status.ps1",
    "//cmk/plugins/printer/agents:win_printers.ps1",
    "windows_if.ps1",
    "//cmk/plugins/windows/agents:windows_multipath.ps1",
    "windows_os_bonding.ps1",
    "//cmk/plugins/windows/agents:windows_tasks.ps1",
    "//cmk/plugins/windows/agents:windows_updates.ps1",
    "hyperv_host.ps1",
]

[
    genrule(
        # n may be a cross-package label; strip the package prefix for
        # the rule name and output path.
        name = "sign_" + n.split(":")[-1],
        srcs = [n],
        outs = ["signed/" + n.split(":")[-1]],
        cmd_bat = "$(execpath scripts/signer.bat) $< $@",
        executable = True,
        target_compatible_with = ["@platforms//os:windows"],
        tools = ["scripts/signer.bat"],
        visibility = ["//visibility:public"],
    )
    for n in TO_SIGN_SCRIPTS
]

pkg_tar(
    name = "signed_plugins",
    srcs = [":sign_" + n.split(":")[-1] for n in TO_SIGN_SCRIPTS],
    strip_prefix = "signed",
    tags = ["manual"],
    target_compatible_with = ["@platforms//os:windows"],
    visibility = ["//visibility:public"],
)

sh_library(
    name = "agents_windows_plugins_sh",
    srcs = [
        ".f12",
    ],
)
