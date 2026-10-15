exports_files(
    [
        "hyperv_vms.ps1",
        "hyperv_vms_guestinfos.ps1",
    ],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = [
        "hyperv_vms.ps1",
        "hyperv_vms_guestinfos.ps1",
    ],
    tags = ["lint-with-psscriptanalyzer"],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
