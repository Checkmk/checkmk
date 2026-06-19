"""Module extension exposing the system glib as @glib.

glib is linked against the distro-provided shared library, so @glib is a
``new_local_repository`` over ``/usr`` with the overlay BUILD applied.  The
overlay's ``select()`` picks the fhs/lsb library paths via @cmk//filesystem_layout.
"""

load("@bazel_tools//tools/build_defs/repo:local.bzl", "new_local_repository")

def _glib_impl(_module_ctx):
    new_local_repository(
        name = "glib",
        build_file = Label("//:BUILD.glib.bazel"),
        path = "/usr",
    )

glib = module_extension(implementation = _glib_impl)
