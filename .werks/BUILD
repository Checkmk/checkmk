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
            # A bytecode cache, e.g. from loading the config as a module, isn't a werk.
            "__pycache__/**",
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
