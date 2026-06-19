"""Macro to package Python wheels into OMD site-packages tarballs."""

load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")

def _package_wheel_impl(
        name,
        whl,
        wheel_tree,
        additional_files,
        visibility):
    """Packages a python wheel into our omd site-packages."""
    if (whl == None) == (wheel_tree == None):
        fail("package_wheel %r: pass exactly one of 'whl' or 'wheel_tree'" % name)

    if whl != None:
        # Extract the wheel into a TreeArtifact ourselves.
        wheel_src = name + "_fg"
        whl_filegroup(
            name = wheel_src,
            whl = whl,
        )
        strip = wheel_src
    else:
        # The caller provides the extracted wheel TreeArtifact, optionally
        # patched (e.g. via set_runpath_tree). It must be a same-package target,
        # so its name is the TreeArtifact's own directory name to strip below.
        wheel_src = wheel_tree
        strip = wheel_tree.name

    # Package the wheel TreeArtifact directly with pkg_tar (instead of going
    # through pkg_files) so the original file permissions are kept: pkg_files
    # forces a fixed mode on every entry, which would strip e.g. the executable
    # bit off shared libraries. package_dir installs the contents under
    # site-packages, strip_prefix removes the TreeArtifact's own directory name.
    wheel_tar_name = name + "_wheel_tar"
    pkg_tar(
        name = wheel_tar_name,
        srcs = [wheel_src],
        package_dir = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = strip,
        mtime = 1767744000,
        portable_mtime = False,
    )

    # Merge the wheel tar with any additional files. The additional files keep
    # their own destinations (e.g. bin/, share/) outside site-packages, and the
    # wheel tar is merged verbatim via deps so it is not affected by them.
    pkg_tar(
        name = name,
        srcs = additional_files,
        deps = [wheel_tar_name],
        mtime = 1767744000,
        portable_mtime = False,
        visibility = visibility,
    )

package_wheel = macro(
    implementation = _package_wheel_impl,
    attrs = {
        "additional_files": attr.label_list(default = [], doc = "List of additional files to put in the tar."),
        "wheel_tree": attr.label(
            # Non-configurable so the implementation gets a plain Label whose
            # name we can use as the strip_prefix.
            configurable = False,
            doc = "Pre-extracted (and possibly patched, e.g. via set_runpath_tree) wheel " +
                  "TreeArtifact to package. Must be a same-package target. Mutually exclusive with 'whl'.",
        ),
        "whl": attr.label(doc = "Wheel to be packaged. Mutually exclusive with 'wheel_tree'."),
    },
)
