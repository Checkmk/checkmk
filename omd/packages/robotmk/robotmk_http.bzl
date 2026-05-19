load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.3"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/all_executables.zip",
        ],
        sha256 = "dd3ba948b35f92048328b1556238448c17d2259dfec6ba2eb9cd357efba3748a",
    )
