load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.0"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/all_executables.zip",
        ],
        sha256 = "f2f1b9174cf34a3479cf5a1453270b04ad25e4ad8ca4bdd4e12af99485d1e2a9",
    )
