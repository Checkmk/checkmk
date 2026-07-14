exports_files(
    [
        "ad_replication.bat",
        "win_dhcp_pools.bat",
        "win_license.bat",
        "windows_broadcom_bonding.bat",
        "windows_multipath.ps1",
        "windows_tasks.ps1",
        "windows_updates.ps1",
    ],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = [
        "windows_multipath.ps1",
        "windows_tasks.ps1",
        "windows_updates.ps1",
    ],
    tags = ["lint-with-psscriptanalyzer"],
)
