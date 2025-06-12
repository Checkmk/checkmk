cc_import(
    name = "libxml2_shared",
    shared_library = select(
        {
            "@//bazel/cmk/filesystem_layout:lsb": "lib/x86_64-linux-gnu/libxml2.so",
            "@//bazel/cmk/filesystem_layout:fhs": "lib64/libxml2.so",
        },
        no_match_error = "Please build with lsb or fhs filesystem layout",
    ),
)

cc_library(
    name = "libxml2",
    hdrs = glob(["include/libxml2/**"]),
    includes = ["include/libxml2"],
    visibility = ["//visibility:public"],
    deps = [
        ":libxml2_shared",
    ],
)
