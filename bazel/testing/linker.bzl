load("@bazel_skylib//rules:write_file.bzl", "write_file")

def test_has_dynamic_library(name, src, pattern):
    name_sh = name + ".sh"
    write_file(
        # We use perl instead of grep because we want perl regex
        # instead of shell ones.
        name = name + "_has_dyn",
        out = name_sh,
        content = ['ldd $1 | perl -0ne "exit 1 unless /$2/"'],
    )
    native.sh_test(
        name = name,
        srcs = [name_sh],
        args = ["$(location %s)" % src, pattern],
        data = [src],
    )

def test_no_dynamic_library(name, src, pattern, tags = []):
    name_sh = name + ".sh"
    write_file(
        # We use perl instead of grep because we want perl regex
        # instead of shell ones.
        name = name + "_no_dyn",
        out = name_sh,
        content = ['ldd $1 | perl -0ne "exit 1 if /$2/"'],
    )
    native.sh_test(
        name = name,
        srcs = [name_sh],
        args = ["$(location %s)" % src, pattern],
        data = [src],
        tags = tags,
    )
