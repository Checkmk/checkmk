load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@bazel_skylib//rules:write_file.bzl", "write_file")

filegroup(
    name = "cfg_examples",
    srcs = glob(
        ["cfg_examples/**"],
        exclude = [
            "**/OWNERS",
        ],
    ),
    visibility = ["//visibility:public"],
)

filegroup(
    name = "mrpe",
    srcs = glob(["mrpe/**"]),
    visibility = ["//visibility:public"],
)

# Artifacts that still require a Windows build node; faked when
# --//:use_faked_artifacts is set.  python-3.cab is NOT in this list: it builds
# hermetically on Linux via //agents/modules/windows:python_3_cab, so it is
# always the real cab (see :python_cab below), never faked.
WINDOWS_ARTIFACTS = [
    "check_mk.user.yml",
    "check_mk_agent.msi",
    "mk-sql.exe",
    "robotmk_ext.exe",
    "unsign-msi.patch",
    "windows_files_hashes.txt",
]

[write_file(
    name = artifact + "_write",
    out = artifact + ".faked",
    content = ["This artifact was faked during the build process by bazel."],
    visibility = ["//omd:__subpackages__"],
) for artifact in WINDOWS_ARTIFACTS]

# The rule outputs python_3_cab.cab; the package expects python-3.cab.
copy_file(
    name = "python_cab",
    src = "//agents/modules/windows:python_3_cab",
    out = "python-3.cab",
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "agents",
    srcs = select({
        "@//:use_fake_artifacts_enabled": [artifact + ".faked" for artifact in WINDOWS_ARTIFACTS],
        "//conditions:default": WINDOWS_ARTIFACTS,
    }) + [":python_cab"],
    tags = ["no-python-extension-checker"],
    visibility = ["//omd:__subpackages__"],
)
