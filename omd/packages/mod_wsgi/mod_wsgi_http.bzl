load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def mod_wsgi(version_str, sha256):
    filename = "mod-wsgi_" + version_str + ".orig.tar.gz"
    http_archive(
        name = "mod_wsgi",
        build_file = "@omd_packages//omd/packages/mod_wsgi:BUILD.mod_wsgi.bazel",
        strip_prefix = "mod_wsgi-" + version_str,
        urls = [
            "http://ftp.debian.org/debian/pool/main/m/mod-wsgi/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        patches = [
            "//omd/packages/mod_wsgi/patches:0001-wsgi_fixVersionCheck.dif",
            "//omd/packages/mod_wsgi/patches:0002-Migrate-from-distutils-to-setuptools-sysconfig.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        sha256 = sha256,
    )
