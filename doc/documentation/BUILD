filegroup(
    name = "srcs",
    srcs = glob(
        include = ["**"],
        exclude = [
            "_*/**",
            ".*",
            "OWNERS",
            "BUILD",
        ],
    ),
    visibility = ["//:__subpackages__"],
)
