load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def mod_wsgi_workspace():
    version_str = "5.0.2"
    filename = "mod-wsgi_" + version_str + ".orig.tar.gz"
    http_archive(
        name = "mod_wsgi",
        build_file = "@omd_packages//omd/packages/mod_wsgi:BUILD.mod_wsgi.bazel",
        strip_prefix = "mod_wsgi-" + version_str,
        urls = [
            "http://ftp.debian.org/debian/pool/main/m/mod-wsgi/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "9a0fdb61405abc300ec6b100c440dd98cf31cb5f97aeef4207390937298cad20",
    )
