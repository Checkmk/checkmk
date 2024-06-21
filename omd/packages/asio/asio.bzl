load("@omd_packages//omd/packages/rules:local_archive.bzl", "local_archive")

def asio(version, sha256):
    # Newer versions available from https://registry.bazel.build/modules/asio
    filename = "asio-" + version
    local_archive(
        name = "asio",
        src = "//:third_party/asio/" + filename + ".tar.gz",
        sha256 = sha256,
        strip_prefix = filename,
        build_file = "@omd_packages//omd/packages/asio:BUILD.asio.bazel",
    )
