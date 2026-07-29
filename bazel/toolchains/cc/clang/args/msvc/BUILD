# MSVC-style action arguments for Bazel-driven cc_* actions.
#
# Bazel's built-in legacy features emit GNU-style driver arguments (-c/-o,
# -iquote, -MD -MF, ar rcsD, ...) that clang-cl/lld-link/llvm-lib do not accept.
# Each cc_feature here `overrides` one of them with an MSVC-style equivalent, or
# with nothing where the concept is GNU-only.
#
# Expected to be superseded by upstream MSVC support in rules_cc;
# //bazel/toolchains/cc/clang/xwin/README.md has the tracking issue and the open PR.

load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")
load("@rules_cc//cc/toolchains:feature.bzl", "cc_feature")
load("@rules_cc//cc/toolchains:feature_set.bzl", "cc_feature_set")
load("@rules_cc//cc/toolchains:nested_args.bzl", "cc_nested_args")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

cc_feature_set(
    name = "features",
    all_of = [
        ":compiler_input_flags",
        ":compiler_output_flags",
        ":include_paths",
        ":preprocessor_defines",
        ":dependency_file",
        ":random_seed",
        ":output_execpath_flags",
        ":libraries_to_link",
        ":library_search_directories",
        ":user_link_flags",
        ":runtime_library_search_directories",
        ":shared_flag",
        ":strip_debug_symbols",
        ":archiver_flags",
    ],
)

# ── Compile: input/output ────────────────────────────────────────────────────

cc_feature(
    name = "compiler_input_flags",
    args = [":compile_input"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:compiler_input_flags",
)

cc_args(
    name = "compile_input",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = [
        "/c",
        "{source_file}",
    ],
    format = {"source_file": "@rules_cc//cc/toolchains/variables:source_file"},
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_feature(
    name = "compiler_output_flags",
    args = [":compile_output"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:compiler_output_flags",
)

cc_args(
    name = "compile_output",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["/Fo{output_file}"],
    format = {"output_file": "@rules_cc//cc/toolchains/variables:output_file"},
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_file",
)

# ── Compile: defines and include paths ───────────────────────────────────────

cc_feature(
    name = "preprocessor_defines",
    args = [":preprocessor_defines_args"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:preprocessor_defines",
)

cc_args(
    name = "preprocessor_defines_args",
    actions = ["@rules_cc//cc/toolchains/actions:source_compile_actions"],
    nested = [":iterate_preprocessor_defines"],
)

cc_nested_args(
    name = "iterate_preprocessor_defines",
    args = ["/D{define}"],
    format = {"define": "@rules_cc//cc/toolchains/variables:preprocessor_defines"},
    iterate_over = "@rules_cc//cc/toolchains/variables:preprocessor_defines",
)

cc_feature(
    name = "include_paths",
    args = [":include_paths_args"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:include_paths",
)

cc_args_list(
    name = "include_paths_args",
    args = [
        ":quote_include_paths",
        ":standard_include_paths",
        ":system_include_paths",
    ],
)

# clang-cl has no -iquote; /I is a reasonable superset.
cc_args(
    name = "quote_include_paths",
    actions = ["@rules_cc//cc/toolchains/actions:source_compile_actions"],
    nested = [":iterate_quote_include_paths"],
)

cc_nested_args(
    name = "iterate_quote_include_paths",
    args = [
        "/I",
        "{path}",
    ],
    format = {"path": "@rules_cc//cc/toolchains/variables:quote_include_paths"},
    iterate_over = "@rules_cc//cc/toolchains/variables:quote_include_paths",
)

cc_args(
    name = "standard_include_paths",
    actions = ["@rules_cc//cc/toolchains/actions:source_compile_actions"],
    nested = [":iterate_standard_include_paths"],
)

cc_nested_args(
    name = "iterate_standard_include_paths",
    args = [
        "/I",
        "{path}",
    ],
    format = {"path": "@rules_cc//cc/toolchains/variables:include_paths"},
    iterate_over = "@rules_cc//cc/toolchains/variables:include_paths",
)

cc_args(
    name = "system_include_paths",
    actions = ["@rules_cc//cc/toolchains/actions:source_compile_actions"],
    nested = [":iterate_system_include_paths"],
)

cc_nested_args(
    name = "iterate_system_include_paths",
    args = [
        "/imsvc",
        "{path}",
    ],
    format = {"path": "@rules_cc//cc/toolchains/variables:system_include_paths"},
    iterate_over = "@rules_cc//cc/toolchains/variables:system_include_paths",
)

# ── Compile: GNU-only concepts replaced with nothing ─────────────────────────

# Header dependencies come from /showIncludes parsing.
cc_feature(
    name = "dependency_file",
    overrides = "@rules_cc//cc/toolchains/features/legacy:dependency_file",
)

# -frandom-seed is not accepted by clang-cl.
cc_feature(
    name = "random_seed",
    overrides = "@rules_cc//cc/toolchains/features/legacy:random_seed",
)

# ── Link ─────────────────────────────────────────────────────────────────────

cc_feature(
    name = "output_execpath_flags",
    args = [":link_output"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:output_execpath_flags",
)

cc_args(
    name = "link_output",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["/OUT:{output_execpath}"],
    format = {"output_execpath": "@rules_cc//cc/toolchains/variables:output_execpath"},
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

cc_feature(
    name = "libraries_to_link",
    args = [
        ":link_libraries",
        ":ar_libraries",
    ],
    overrides = "@rules_cc//cc/toolchains/features/legacy:libraries_to_link",
)

cc_args(
    name = "link_libraries",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    nested = [":iterate_libraries_to_link"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:libraries_to_link",
)

cc_feature(
    name = "library_search_directories",
    args = [":library_search_directories_args"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:library_search_directories",
)

cc_args(
    name = "library_search_directories_args",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["/LIBPATH:{path}"],
    format = {"path": "@rules_cc//cc/toolchains/variables:library_search_directories"},
    iterate_over = "@rules_cc//cc/toolchains/variables:library_search_directories",
    requires_not_none = "@rules_cc//cc/toolchains/variables:library_search_directories",
)

cc_feature(
    name = "user_link_flags",
    args = [":user_link_flags_args"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:user_link_flags",
)

cc_args(
    name = "user_link_flags_args",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["{user_link_flags}"],
    format = {"user_link_flags": "@rules_cc//cc/toolchains/variables:user_link_flags"},
    iterate_over = "@rules_cc//cc/toolchains/variables:user_link_flags",
    requires_not_none = "@rules_cc//cc/toolchains/variables:user_link_flags",
)

# ── Link: GNU-only concepts replaced with nothing ────────────────────────────

# No rpath on Windows.
cc_feature(
    name = "runtime_library_search_directories",
    overrides = "@rules_cc//cc/toolchains/features/legacy:runtime_library_search_directories",
)

# DLLs are not supported yet.
cc_feature(
    name = "shared_flag",
    args = [":shared_unsupported"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:shared_flag",
)

cc_args(
    name = "shared_unsupported",
    actions = ["@rules_cc//cc/toolchains/actions:dynamic_library_link_actions"],
    args = ["DLLS-NOT-SUPPORTED-BY-XWIN-TOOLCHAIN-see-args-msvc-BUILD-shared_flag"],
)

# -Wl,-S is GNU; PDB handling is a separate concern.
cc_feature(
    name = "strip_debug_symbols",
    overrides = "@rules_cc//cc/toolchains/features/legacy:strip_debug_symbols",
)

# ── Archive (llvm-lib) ───────────────────────────────────────────────────────

cc_feature(
    name = "archiver_flags",
    args = [":ar_output"],
    overrides = "@rules_cc//cc/toolchains/features/legacy:archiver_flags",
)

cc_args(
    name = "ar_output",
    actions = ["@rules_cc//cc/toolchains/actions:cpp_link_static_library"],
    args = ["/OUT:{output_execpath}"],
    format = {"output_execpath": "@rules_cc//cc/toolchains/variables:output_execpath"},
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

cc_args(
    name = "ar_libraries",
    actions = ["@rules_cc//cc/toolchains/actions:cpp_link_static_library"],
    nested = [":iterate_libraries_to_link"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:libraries_to_link",
)

# ── libraries_to_link ────────────────────────────────────────────────────────

cc_nested_args(
    name = "iterate_libraries_to_link",
    iterate_over = "@rules_cc//cc/toolchains/variables:libraries_to_link",
    nested = [
        ":object_file_group",
        ":object_file",
        ":static_library",
        ":whole_archive_static_library",
        ":interface_library",
        ":dynamic_library",
    ],
)

cc_nested_args(
    name = "object_file_group",
    args = ["{object}"],
    format = {"object": "@rules_cc//cc/toolchains/variables:libraries_to_link.object_files"},
    iterate_over = "@rules_cc//cc/toolchains/variables:libraries_to_link.object_files",
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "object_file_group",
)

cc_nested_args(
    name = "object_file",
    args = ["{name}"],
    format = {"name": "@rules_cc//cc/toolchains/variables:libraries_to_link.name"},
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "object_file",
)

cc_nested_args(
    name = "static_library",
    nested = [":plain_static_library"],
    requires_false = "@rules_cc//cc/toolchains/variables:libraries_to_link.is_whole_archive",
)

cc_nested_args(
    name = "plain_static_library",
    args = ["{name}"],
    format = {"name": "@rules_cc//cc/toolchains/variables:libraries_to_link.name"},
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "static_library",
)

cc_nested_args(
    name = "whole_archive_static_library",
    nested = [":wholearchive_static_library"],
    requires_true = "@rules_cc//cc/toolchains/variables:libraries_to_link.is_whole_archive",
)

cc_nested_args(
    name = "wholearchive_static_library",
    args = ["/WHOLEARCHIVE:{name}"],
    format = {"name": "@rules_cc//cc/toolchains/variables:libraries_to_link.name"},
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "static_library",
)

cc_nested_args(
    name = "interface_library",
    args = ["{name}"],
    format = {"name": "@rules_cc//cc/toolchains/variables:libraries_to_link.name"},
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "interface_library",
)

cc_nested_args(
    name = "dynamic_library",
    args = ["{name}"],
    format = {"name": "@rules_cc//cc/toolchains/variables:libraries_to_link.name"},
    requires_equal = "@rules_cc//cc/toolchains/variables:libraries_to_link.type",
    requires_equal_value = "dynamic_library",
)
