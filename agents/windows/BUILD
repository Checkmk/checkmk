load("@bazel_skylib//rules:write_file.bzl", "write_file")

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

WINDOWS_ARTIFACTS = [
    "check_mk.user.yml",
    "check_mk_agent.msi",
    "mk-sql.exe",
    "python-3.cab",
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

filegroup(
    name = "agents",
    srcs = select({
        "@//:use_fake_artifacts_enabled": [artifact + ".faked" for artifact in WINDOWS_ARTIFACTS],
        "//conditions:default": WINDOWS_ARTIFACTS,
    }),
    visibility = ["//omd:__subpackages__"],
)
