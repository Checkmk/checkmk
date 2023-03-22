load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def stunnel(version_str, sha256):
    http_archive(
        name="stunnel",
        build_file="@omd_packages//packages/stunnel:BUILD.stunnel.bazel",
        strip_prefix="stunnel-" + version_str,
        url="https://ftp.nluug.nl/pub/networking/stunnel/archive/5.x/stunnel-"+ version_str + ".tar.gz",
        sha256=sha256,
    )
