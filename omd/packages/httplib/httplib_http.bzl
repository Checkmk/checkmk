load("//bazel/rules:local_archive.bzl", "local_archive")

def httplib_workspace():
    version_str = "0.13.3"
    local_archive(
        name = "httplib",
        src = "//:omd/packages/httplib/cpp-httplib-" + version_str + ".tar.gz",
        sha256 = "2a4503f9f2015f6878baef54cd94b01849cc3ed19dfe95f2c9775655bea8b73f",
        strip_prefix = "cpp-httplib-" + version_str,
        build_file = "//:omd/packages/httplib/BUILD",
    )
