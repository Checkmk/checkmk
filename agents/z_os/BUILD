filegroup(
    name = "srcs",
    srcs = glob(
        ["**"],
        exclude = [
            "BUILD",
            "**/OWNERS",
        ],
    ),
    visibility = ["//visibility:public"],
)

sh_library(
    name = "agents_z_os_sh",
    srcs = [
        "check_mk_agent.wrapper",
    ],
)
