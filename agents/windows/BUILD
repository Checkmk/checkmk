filegroup(
    name = "cfg_examples",
    srcs = glob(
        ["cfg_examples/**"],
        exclude = [
            "**/OWNERS",
            "**/.f12",
        ],
    ),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "mrpe",
    srcs = glob(["mrpe/**"]),
    visibility = ["//visibility:public"],
)

# HACK
# * windows agents need to be build on Windows
# * that's why we pre-built it on Windows before-hand and put it in the workspace
# * see package_helper.groovy
# TODO: Please let bazel take over building on windows remotly eventually...
filegroup(
    name = "agents",
    srcs = [
        "check_mk.user.yml",
        "check_mk_agent.msi",
        "mk-sql.exe",
        "python-3.cab",
        "robotmk_ext.exe",
        "unsign-msi.patch",
        "windows_files_hashes.txt",
    ],
    visibility = ["//omd:__subpackages__"],
)
