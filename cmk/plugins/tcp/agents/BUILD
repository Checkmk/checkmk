exports_files(
    ["netstat_an.bat"],
    visibility = ["//agents/windows/plugins:__pkg__"],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = [
        "netstat.aix",
        "netstat.linux",
        "netstat.solaris",
    ],
)

filegroup(
    name = "files",
    srcs = glob(
        ["*"],
        exclude = ["BUILD"],
    ),
    visibility = ["//cmk/plugins:__pkg__"],
)
