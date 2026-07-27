# Referenced by //:root_sh, which lived in the root package before this BUILD
# file turned third_party into a package of its own.
exports_files(glob(["*/create-archive"]))

filegroup(
    name = "third_party_archives",
    srcs = glob(
        [
            "**/*.tar.gz",
            "**/*.zip",
        ],
    ),
    visibility = ["//visibility:public"],
)
