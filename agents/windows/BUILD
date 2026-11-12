load("@bazel_skylib//rules:copy_file.bzl", "copy_file")

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
# python-3.cab is the exception: it builds hermetically on Linux via
# //agents/modules/windows:python_3_cab, so it's always built for real here.

# Taken from the source tree: no build needed.
copy_file(
    name = "check_mk_user_yml",
    src = "//agents/wnx:install/resources/check_mk.user.yml",
    out = "check_mk.user.yml",
)

# The rule outputs python_3_cab.cab; the package expects python-3.cab.
copy_file(
    name = "python_cab",
    src = "//agents/modules/windows:python_3_cab",
    out = "python-3.cab",
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "agents",
    srcs = [
        "check_mk_agent.msi",
        "mk-sql.exe",
        "robotmk_ext.exe",
        "unsign-msi.patch",
        "windows_files_hashes.txt",
    ] + [
        ":check_mk_user_yml",
        ":python_cab",
    ],
    visibility = ["//omd:__subpackages__"],
)
