load("@bazel_skylib//rules:copy_file.bzl", "copy_file")

exports_files(["skel.permissions"])

# Re-emit the module-built tarball from this package so its output path stays
# //omd/packages/perl-modules/perl-modules.tar.  Consumers (net-snmp, rrdtool)
# derive directory paths from this location, so it must not move into the
# external @perl-modules repo tree.
copy_file(
    name = "perl-modules",
    src = "@perl-modules//:perl-modules",
    out = "perl-modules.tar",
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
