cc_library(
    name = "glibconfig",
    hdrs = glob([
        # buildifier: disable=constant-glob
        "lib/x86_64-linux-gnu/glib-2.0/include/glibconfig.h",
        "lib64/glib-2.0/include/glibconfig.h",
    ]),
    includes = glob(
        [
            # buildifier: disable=constant-glob
            # glibconfig.h path for most distros, including Ubuntu
            "lib/x86_64-linux-gnu/glib-2.0/include",
            # glibconfig.h path for el{8,9] and sles15* distros
            "lib64/glib-2.0/include",
        ],
        exclude_directories = 0,
    ),
)

cc_library(
    name = "glib_headers",
    hdrs = glob(["include/glib-2.0/**"]),
    includes = ["include/glib-2.0"],
    visibility = ["//visibility:public"],
    deps = [":glibconfig"],
)
