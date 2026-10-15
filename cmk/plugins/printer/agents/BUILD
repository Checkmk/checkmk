exports_files(
    ["win_printers.ps1"],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = ["win_printers.ps1"],
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
