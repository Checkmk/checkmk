"""Make system glibconfig.h available."""

BUILD = """
package(default_visibility = ["//visibility:public"])
cc_library(
    name = "glibconfig",
    hdrs = ["include/glibconfig.h"],
    includes = ["include"],
)
"""

def glibconfig(name):
    native.new_local_repository(
        name = "glibconfig",
        build_file_content = BUILD,
        path = "/usr/lib/x86_64-linux-gnu/glib-2.0",
    )
