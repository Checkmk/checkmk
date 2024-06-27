"""Make system glibconfig.h available."""

BUILD = """
package(default_visibility = ["//visibility:public"])
cc_library(
    name = "%s",
    hdrs = ["include/glibconfig.h"],
    includes = ["include"],
)
"""

def glibconfig(name, path):
    native.new_local_repository(
        name = name,
        build_file_content = BUILD % name,
        path = path,
    )
