load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def robotmk_workspace():
    version_str = "v3.0.0-alpha-10"
    http_archive(
        name = "robotmk",
        build_file = "//omd/packages/robotmk:BUILD.robotmk.bazel",
        urls = [
            "https://github.com/elabit/robotmk/releases/download/" + version_str + "/executables.zip",
        ],
        sha256 = "8d5eb2f37069f3819c20d12fa8c88556cd456adcedee5127e1e730d974ed12e2",
    )
