load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")

exports_files([
    "Pipfile",
    "Pipfile.lock",
])

# Generate `compile_commands.json` with `bazel run //:refresh_compile_commands`.
refresh_compile_commands(
    name = "refresh_compile_commands",
    targets = {
        # target: build-flags
        "//packages/cmc:cmc": "",
        "//packages/cmc:icmpreceiver": "",
        "//packages/cmc:icmpsender": "",
        "//packages/cmc:checkhelper": "",
        "//packages/neb:neb_shared": "",
    },
)
