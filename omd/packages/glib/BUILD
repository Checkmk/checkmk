cc_library(
    name = "glibconfig",
    hdrs = select(
        {
            "@//:lsb_filesystem_layout": ["lib/x86_64-linux-gnu/glib-2.0/include/glibconfig.h"],
            "@//:fhs_filesystem_layout": ["lib64/glib-2.0/include/glibconfig.h"],
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
    includes = select(
        {
            "@//:lsb_filesystem_layout": ["lib/x86_64-linux-gnu/glib-2.0/include"],
            "@//:fhs_filesystem_layout": ["lib64/glib-2.0/include"],
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
)

cc_library(
    name = "glib_headers",
    hdrs = glob(["include/glib-2.0/**"]),
    includes = ["include/glib-2.0"],
    visibility = ["//visibility:public"],
    deps = [":glibconfig"],
)
