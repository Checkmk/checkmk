load("@aspect_rules_py//py:defs.bzl", "py_library")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "pkg_marker",
    srcs = ["__init__.py"],
    imports = [".."],
    visibility = ["//:__subpackages__"],
)
