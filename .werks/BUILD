filegroup(
    name = ".werks",
    srcs = glob(
        include = ["**"],
        exclude = [
            "BUILD",
            "config",
            "first_free",
            ".gitignore",
            ".last",
        ],
    ),
    visibility = ["//:__subpackages__"],
)

filegroup(
    name = "werks_config",
    srcs = ["config"],
    visibility = ["//:__subpackages__"],
)

filegroup(
    name = "werks_first_free",
    srcs = ["first_free"],
    visibility = ["//:__subpackages__"],
)
