load("@omd_packages//omd/packages/rules:local_archive.bzl", "local_archive")

def httplib(version_str, sha256):
    local_archive(
        name = "httplib",
        src = "//:omd/packages/httplib/cpp-httplib-" + version_str + ".tar.gz",
        sha256 = sha256,
        strip_prefix = "cpp-httplib-" + version_str,
        build_file = "//:omd/packages/httplib/BUILD",
    )
