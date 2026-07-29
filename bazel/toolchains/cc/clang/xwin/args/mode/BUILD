# Compilation-mode arguments for Bazel's own cc_* actions.
#
# -c dbg / -c fastbuild / -c opt reproduce the agents/wnx vcxproj configs.

load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")
load("@rules_cc//cc/toolchains:feature.bzl", "cc_feature")
load("@rules_cc//cc/toolchains:feature_set.bzl", "cc_feature_set")
load("//bazel/toolchains/cc/clang/xwin/args:crt.bzl", "DEBUG_CRT_LINK_ARGS", "RELEASE_CRT_LINK_ARGS")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

# ── Modes ───────────────────────────────────────────────────────────────────

cc_feature_set(
    name = "features",
    all_of = [
        ":dbg",
        ":fastbuild",
        ":opt",
        ":generate_pdb_file",
    ],
)

cc_feature(
    name = "dbg",
    args = [":dbg_args"],
    implies = [":generate_pdb_file"],
    overrides = "@rules_cc//cc/toolchains/features:dbg",
)

cc_args_list(
    name = "dbg_args",
    args = [
        ":no_optimization_args",
        ":embed_debug_info",
        ":link_debug_info",
        ":static_debug_crt",
        ":debug_crt_link",
    ],
)

cc_feature(
    name = "fastbuild",
    args = [":fastbuild_args"],
    overrides = "@rules_cc//cc/toolchains/features:fastbuild",
)

cc_args_list(
    name = "fastbuild_args",
    args = [
        ":no_optimization_args",
        ":static_release_crt",
        ":release_crt_link",
    ],
)

cc_feature(
    name = "opt",
    args = [":opt_args"],
    overrides = "@rules_cc//cc/toolchains/features:opt",
)

cc_args_list(
    name = "opt_args",
    args = [
        ":moderate_optimization_args",
        ":ndebug",
        ":gc_sections",
        ":icf",
        ":static_release_crt",
        ":release_crt_link",
    ],
)

cc_feature(
    name = "generate_pdb_file",
    feature_name = "generate_pdb_file",
)

# ── Optimization and assertions ─────────────────────────────────────────────

cc_args(
    name = "no_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/Od"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "moderate_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/O2"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "ndebug",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["-DNDEBUG"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "gc_sections",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["/OPT:REF"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

# Identical COMDAT folding; no counterpart in the gcc tree to compare against.
cc_args(
    name = "icf",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = ["/OPT:ICF"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

# ── Debug information ───────────────────────────────────────────────────────

cc_args(
    name = "embed_debug_info",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/Z7"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "link_debug_info",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = [
        "/DEBUG",
        "/PDBALTPATH:%_PDB%",
        "/IGNORE:4099",
    ],
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

# ── CRT flavour ─────────────────────────────────────────────────────────────

cc_args(
    name = "static_release_crt",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/MT"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "static_debug_crt",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/MTd"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "release_crt_link",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = RELEASE_CRT_LINK_ARGS,
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)

cc_args(
    name = "debug_crt_link",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = DEBUG_CRT_LINK_ARGS,
    requires_not_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)
