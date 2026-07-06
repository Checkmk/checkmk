"""Macro to package Python wheels into OMD site-packages tarballs."""

load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")
load("//bazel/rules:console_scripts.bzl", "wheel_console_scripts")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

def _package_wheel_impl(
        name,
        whl,
        additional_files,
        visibility):
    """Packages a python wheel into our omd site-packages."""
    whl_filegroup_name = name + "_fg"

    whl_filegroup(
        name = whl_filegroup_name,
        whl = whl,
    )

    # Package the wheel TreeArtifact directly with pkg_tar (instead of going
    # through pkg_files) so the original file permissions are kept: pkg_files
    # forces a fixed mode on every entry, which would strip e.g. the executable
    # bit off shared libraries. package_dir installs the contents under
    # site-packages, strip_prefix removes the TreeArtifact's own directory name.
    wheel_tar_name = name + "_wheel_tar"
    pkg_tar(
        name = wheel_tar_name,
        srcs = [whl_filegroup_name],
        package_dir = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = whl_filegroup_name,
        mtime = 1767744000,
        portable_mtime = False,
    )

    # Generate bin/ console-script wrappers from the wheel's entry points. The wheel
    # records its console_scripts in *.dist-info/entry_points.txt; since we unzip wheels
    # instead of installing them, we materialise the wrappers ourselves. Wheels without
    # console_scripts yield an empty wrapper directory, so this is a no-op for them.
    # The wrapper TreeArtifact is packaged directly with pkg_tar (like the wheel above)
    # so the executable bit is preserved instead of being flattened by pkg_files.
    console_scripts_name = name + "_console_scripts"
    wheel_console_scripts(
        name = console_scripts_name,
        whl = whl,
    )
    bin_tar_name = name + "_bin_tar"
    pkg_tar(
        name = bin_tar_name,
        srcs = [console_scripts_name],
        package_dir = "bin",
        strip_prefix = console_scripts_name,
        mtime = 1767744000,
        portable_mtime = False,
    )
    extra_deps = [wheel_tar_name, bin_tar_name]

    # Merge the wheel tar with any additional files. The additional files keep
    # their own destinations (e.g. bin/, share/) outside site-packages, and the
    # wheel tar is merged verbatim via deps so it is not affected by them.
    pkg_tar(
        name = name,
        srcs = additional_files,
        deps = extra_deps,
        mtime = 1767744000,
        portable_mtime = False,
        visibility = visibility,
    )

package_wheel = macro(
    implementation = _package_wheel_impl,
    attrs = {
        "additional_files": attr.label_list(default = [], doc = "List of additional files to put in the tar."),
        "whl": attr.label(mandatory = True, doc = "Wheel to be packaged."),
    },
)
