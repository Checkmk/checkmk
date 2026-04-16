filegroup(
    name = "gui_srcs",
    srcs = glob(
        include = [
            "*.py",
            "_openapi/**/*.py",
        ],
    ) + [
        "//cmk/gui/sidebar/_snapin:gui_srcs",
    ],
    visibility = ["//cmk/gui:__pkg__"],
)
