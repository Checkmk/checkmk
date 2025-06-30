load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

exports_files([
    "config",
    "templates",
])

debian_files = [
    "links",
    "postinst",
    "postrm",
    "preinst",
    "prerm",
]

[file_from_flag(
    name = file + "_file",
    src = file + ".in",
    out = file,
    replace_labels = {
        "CMK_VERSION": "//bazel/cmk/version",
        "CMK_EDITION": "//bazel/cmk/edition",
    },
    visibility = ["//omd:__pkg__"],
) for file in debian_files]
