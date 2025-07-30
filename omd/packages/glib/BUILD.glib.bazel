cc_library(
    name = "glibconfig",
    hdrs = select(
        {
            "@//bazel/cmk/filesystem_layout:lsb": ["lib/x86_64-linux-gnu/glib-2.0/include/glibconfig.h"],
            "@//bazel/cmk/filesystem_layout:fhs": ["lib64/glib-2.0/include/glibconfig.h"],
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
    includes = select(
        {
            "@//bazel/cmk/filesystem_layout:lsb": ["lib/x86_64-linux-gnu/glib-2.0/include"],
            "@//bazel/cmk/filesystem_layout:fhs": ["lib64/glib-2.0/include"],
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
)

cc_import(
    name = "libglib",
    shared_library = select(
        {
            "@//bazel/cmk/filesystem_layout:lsb": "lib/x86_64-linux-gnu/libglib-2.0.so",
            "@//bazel/cmk/filesystem_layout:fhs": "lib64/libglib-2.0.so",
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
)

cc_library(
    name = "glib",
    hdrs = glob(["include/glib-2.0/**"]),
    includes = ["include/glib-2.0"],
    visibility = ["//visibility:public"],
    deps = [
        ":glibconfig",
        ":libglib",
    ],
)
