"""Macro to rename Bazel-downloaded Perl packages to their original names."""

load("@package_metadata//rules:package_metadata.bzl", "package_metadata")

def rename_perl_package(name, srcs, outs, **kwargs):
    """This macro is renaming the packages to their original name.

    The Perl installation process needs archive to be named
    `name_version.tar.gz`. Bazel renames downloaded archives to `downloaded`.
    """
    package_name, package_version = name.rstrip(".").rsplit("-", 1)
    package_metadata(
        name = "{}-package_metadata".format(name),
        # This is very hacky but IMHO fits our current packages, might be improved as soon as we see gaps
        purl = "pkg:cpan/{}@{}".format(package_name.replace("-", "%3A%3A"), package_version),
        attributes = [],
    )
    native.genrule(
        name = name,
        srcs = srcs,
        outs = outs,
        cmd = """
            cp $< $@
        """,
        package_metadata = [
            ":{}-package_metadata".format(name),
        ],
        **kwargs
    )
