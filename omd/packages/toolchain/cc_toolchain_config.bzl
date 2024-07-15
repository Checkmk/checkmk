"""Configuration of our CC toolchains."""

load(
    "@bazel_tools//tools/cpp:unix_cc_toolchain_config.bzl",
    unix_cc_toolchain_config = "cc_toolchain_config",
)

def cc_toolchain_config(
        name,
        tool_paths,
        compiler,
        toolchain_identifier,
        cxx_builtin_include_directories):
    """Wrapper for unix_cc_toolchain_config.

    Sets defaults taken from the local builtin toolchain.

    Args:
        name: Forwarded to unix_cc_toolchain_config
        tool_paths: Forwarded to unix_cc_toolchain_config
        compiler: Forwarded to unix_cc_toolchain_config
        toolchain_identifier: Forwarded to unix_cc_toolchain_config
        cxx_builtin_include_directories: Forwarded to unix_cc_toolchain_config

    """
    compile_flags = [
        "-fstack-protector",
        "-Wall",
        "-Wunused-but-set-parameter",
        "-Wno-free-nonheap-object",
        "-fno-omit-frame-pointer",
    ]
    cxx_flags = ["-std=c++20"]
    dbg_compile_flags = ["-g"]
    link_flags = [
        "-fuse-ld=gold",
        "-Wl,-no-as-needed",
        "-Wl,-z,relro,-z,now",
        "-pass-exit-codes",
    ]
    link_libs = ["-lstdc++", "-lm"]
    opt_compile_flags = [
        "-g0",
        "-O2",
        "-D_FORTIFY_SOURCE=1",
        "-DNDEBUG",
        "-ffunction-sections",
        "-fdata-sections",
    ]
    opt_link_flags = ["-Wl,--gc-sections"]
    unfiltered_compile_flags = [
        "-fno-canonical-system-headers",
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ]

    # We use unix_cc_toolchain_config[1] but the builtin toolchain[2] could be another
    # starting point.
    #
    # [1] https://cs.opensource.google/bazel/bazel/+/master:tools/cpp/unix_cc_toolchain_config.bzl
    # [2] https://cs.opensource.google/bazel/bazel/+/master:tools/cpp/unix_cc_configure.bzl
    unix_cc_toolchain_config(
        name = name,
        cpu = "k8",
        compiler = compiler,
        toolchain_identifier = toolchain_identifier,
        host_system_name = "local",
        target_system_name = "local",
        target_libc = "local",
        abi_version = "local",
        abi_libc_version = "local",
        cxx_builtin_include_directories = cxx_builtin_include_directories,
        tool_paths = tool_paths,
        compile_flags = compile_flags,
        dbg_compile_flags = dbg_compile_flags,
        opt_compile_flags = opt_compile_flags,
        cxx_flags = cxx_flags,
        link_flags = link_flags,
        link_libs = link_libs,
        opt_link_flags = opt_link_flags,
        unfiltered_compile_flags = unfiltered_compile_flags,
    )
