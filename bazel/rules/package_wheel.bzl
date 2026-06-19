"""Macro to package Python wheels into OMD site-packages tarballs."""

load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")
load("//bazel/rules:patchelf.bzl", "set_runpath_tree")

def _package_wheel_impl(
        name,
        whl,
        additional_files,
        rpath,
        visibility):
    """Packages a python wheel into our omd site-packages."""
    whl_filegroup_name = name + "_fg"

    whl_filegroup(
        name = whl_filegroup_name,
        whl = whl,
    )

    if rpath:
        runpath_name = name + "_runpath"
        set_runpath_tree(
            name = runpath_name,
            src = ":" + whl_filegroup_name,
            rpath = rpath,
        )
        wheel_src = runpath_name
    else:
        wheel_src = whl_filegroup_name

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
        strip_prefix = wheel_src,
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
        "rpath": attr.string(
            default = "",
            doc = "When non-empty, patch all ELF .so files in the wheel with this RUNPATH via set_runpath_tree.",
        ),
        "whl": attr.label(mandatory = True, doc = "Wheel to be packaged."),
    },
)
