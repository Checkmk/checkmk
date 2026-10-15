exports_files(
    [
        "msexch_dag.ps1",
        "msexch_database.ps1",
    ],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

filegroup(
    name = "powershell_scripts",
    srcs = [
        "msexch_dag.ps1",
        "msexch_database.ps1",
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
