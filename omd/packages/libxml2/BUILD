cc_import(
    name = "libxml2_shared",
    shared_library = select(
        {
            "@//:lsb_filesystem_layout": "lib/x86_64-linux-gnu/libxml2.so",
            "@//:fhs_filesystem_layout": "lib64/libxml2.so",
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
