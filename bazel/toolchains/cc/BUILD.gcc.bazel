# Copyright 2025 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

load("@bazel_skylib//rules/directory:directory.bzl", "directory")
load("@bazel_skylib//rules/directory:subdirectory.bzl", "subdirectory")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

exports_files(glob(["bin/**"]))

# Directory-based rules in this toolchain only referece things in
# lib/ or include/ subdirectories.
directory(
    name = "toolchain_root",
    srcs = glob([
        "lib/**",
        "x86_64-buildroot-linux-gnu/include/**",
    ]),
)

subdirectory(
    name = "lib-gcc-include",
    parent = ":toolchain_root",
    path = "x86_64-buildroot-linux-gnu/include",
)

subdirectory(
    name = "include-x86_64-buildroot-linux-gnu",
    parent = ":toolchain_root",
    path = "lib/gcc/x86_64-buildroot-linux-gnu/13.3.0/include",
)

filegroup(
    name = "builtin_headers",
    srcs = [
        ":include-x86_64-buildroot-linux-gnu",
        ":lib-gcc-include",
    ],
)

# Various supporting files needed to run the linker.
filegroup(
    name = "linker_builtins",
    data = glob([
        "bin/*ld*",
        "lib/**/*.a",
        "lib/**/*.so*",
        "lib/**/*.o",
    ]),
)

# Some toolchain distributions use busybox-style handling of tools, so things
# like `g++` just redirect to a different binary. This glob catches this
# binary if it's included in the distribution, and is a no-op if the multicall
# binary doesn't exist.
filegroup(
    name = "multicall_support_files",
    srcs = glob([
        "libexec/**/*",
    ]),
)

directory(
    name = "root",
    srcs = glob(["x86_64-buildroot-linux-gnu/sysroot/**/*"]),
)

subdirectory(
    name = "sysroot",
    parent = ":root",
    path = "x86_64-buildroot-linux-gnu/sysroot",
)
