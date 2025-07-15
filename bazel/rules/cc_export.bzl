"""Export a library from an output group."""

def _cc_export_shared_library_impl(
        name,
        srcs,
        shared_library,
        visibility):
    filegroup_name = name + "_fg"
    native.filegroup(
        name = filegroup_name,
        srcs = srcs,
        output_group = shared_library,
        visibility = ["//visibility:private"],
    )
    native.cc_import(
        name = name,
        shared_library = filegroup_name,
        visibility = visibility,
    )

cc_export_shared_library = macro(
    doc = """Export shared library from output group.

    Args:
        name: Name of this target.
        srcs: List of labels.  See filegroups.
        shared_library: Library to export.
        visibility: The visibility attribute on the target.

    """,
    implementation = _cc_export_shared_library_impl,
    attrs = {
        "srcs": attr.label_list(mandatory = True),
        "shared_library": attr.string(mandatory = True),
    },
)

def _cc_export_static_library_impl(
        name,
        srcs,
        static_library,
        visibility):
    filegroup_name = name + "_fg"
    native.filegroup(
        name = filegroup_name,
        srcs = srcs,
        output_group = static_library,
        visibility = ["//visibility:private"],
    )
    native.cc_import(
        name = name,
        static_library = filegroup_name,
        alwayslink = 1,
        visibility = visibility,
    )

cc_export_static_library = macro(
    doc = """Export static library from output group.

    Args:
        name: Name of this target.
        srcs: List of labels.  See filegroups.
        static_library: Library to export.
        visibility: The visibility attribute on the target.

    """,
    implementation = _cc_export_static_library_impl,
    attrs = {
        "srcs": attr.label_list(mandatory = True),
        "static_library": attr.string(mandatory = True),
    },
)
