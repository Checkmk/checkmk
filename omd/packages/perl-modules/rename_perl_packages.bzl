def rename_perl_package(name, srcs, outs, **kwargs):
    """This macro is renaming the packages to their original name.

    The Perl installation process needs archive to be named
    `name_version.tar.gz`. Bazel renames downloaded archives to `downloaded`.
    """
    native.genrule(
        name = name,
        srcs = srcs,
        outs = outs,
        cmd = """
            cp $< $@
        """,
        **kwargs
    )
