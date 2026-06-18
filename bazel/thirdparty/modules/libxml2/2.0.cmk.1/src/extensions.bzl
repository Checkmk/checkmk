"""Module extension exposing the system libxml2 as @libxml2.

libxml2 is linked against the distro-provided shared library, so @libxml2 is a
``new_local_repository`` over ``/usr`` with the overlay BUILD applied.  The
overlay's ``select()`` picks the fhs/lsb library paths via @cmk//filesystem_layout.
"""

load("@bazel_tools//tools/build_defs/repo:local.bzl", "new_local_repository")

def _libxml2_impl(_module_ctx):
    new_local_repository(
        name = "libxml2",
        build_file = Label("//:BUILD.libxml2.bazel"),
        path = "/usr",
    )

libxml2 = module_extension(implementation = _libxml2_impl)
