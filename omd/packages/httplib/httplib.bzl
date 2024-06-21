load("@omd_packages//omd/packages/rules:local_archive.bzl", "local_archive")

def httplib(version, sha256):
    local_archive(
        name = "httplib",
        src = "//:omd/packages/httplib/cpp-httplib-" + version + ".tar.gz",
        sha256 = sha256,
        strip_prefix = "cpp-httplib-" + version,
        build_file = "//:omd/packages/httplib/BUILD",
    )
