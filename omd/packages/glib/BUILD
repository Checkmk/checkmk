package(default_visibility = ["//visibility:public"])

cc_library(
    name = "glib_headers",
    hdrs = glob([
        "include/glib-2.0/**",
        "lib/x86_64-linux-gnu/glib-2.0/include/glibconfig.h",  # buildifier: disable=constant-glob
        "lib64/glib-2.0/include/glibconfig.h",
    ]),
    includes = ([
        # path for general glib headers, seems to be distro-independent
        "include/glib-2.0",
    ] + glob(
        [
            # glibconfig.h path for most distros, including Ubuntu
            "lib/x86_64-linux-gnu/glib-2.0/include",  # buildifier: disable=constant-glob
            # glibconfig.h path for el{8,9] and sles15* distros
            "lib64/glib-2.0/include",
        ],
        exclude_directories = 0,
    )),
)
