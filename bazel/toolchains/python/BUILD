# Python toolchain fallback for the Windows execution platform.
#
# rules_pkg's build_zip (a py_binary used by pkg_zip, e.g.
# //omd/packages/oci:oci_light_win_x64) needs a
# @bazel_tools//tools/python:toolchain_type for the *execution* platform.
# In legacy WORKSPACE mode this was satisfied by Bazel's implicitly registered
# autodetecting Python toolchain.  Under --noenable_workspace that implicit
# registration is gone; rules_python's hermetic toolchains cover the Linux exec
# platform but not the Windows build agent.
#
# Scope a runtime-environment Python toolchain to the Windows exec platform only,
# mirroring what WORKSPACE mode provided there.  Because it is constrained to
# Windows exec it never shadows the hermetic interpreter used on Linux.
toolchain(
    name = "runtime_env_python_windows",
    exec_compatible_with = ["@platforms//os:windows"],
    toolchain = "@rules_python//python/runtime_env_toolchains:_runtime_env_py_runtime_pair",
    toolchain_type = "@bazel_tools//tools/python:toolchain_type",
)
