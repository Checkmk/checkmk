load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

exports_files([
    "config",
    "templates",
])

debian_files = [
    "postinst",
    "postrm",
    "preinst",
    "prerm",
    "triggers",
]

[file_from_flag(
    name = file + "_file",
    src = file + ".in",
    out = file,
    replace_labels = {
        "CMK_EDITION": "@cmk//edition",
        "CMK_VERSION": "@cmk//version",
    },
    visibility = ["//omd:__pkg__"],
) for file in debian_files]

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = [
        "preinst.in",
    ],
)
