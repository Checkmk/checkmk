"""`py_package` drop-in that filters collected sources by their Bazel target owner.

Stock `py_package` filters by *Python import path* (`packages = ["cmk"]` keeps any file whose in-wheel
path starts with `cmk/`). That is too coarse when several Bazel packages share an import namespace but
ship in separate wheels (e.g. //packages/cmk-ccc exposes `cmk.ccc.*`). This rule filters by *Bazel
target owner* instead: it walks the transitive Python sources of its deps and keeps only files whose
owning target sits under one of `include_roots`.
"""

load("@rules_python//python:defs.bzl", "PyInfo")

def _under_root(pkg, include_roots):
    pkg_slash = pkg + "/"
    for root in include_roots:
        if pkg_slash.startswith(root + "/"):
            return True
    return False

def _collect_inputs(deps):
    """Mirror py_package's input collection: runfiles + PyInfo source sets."""
    transitive = []
    for dep in deps:
        transitive.append(dep[DefaultInfo].data_runfiles.files)
        transitive.append(dep[DefaultInfo].default_runfiles.files)
        if PyInfo in dep:
            info = dep[PyInfo]
            transitive.append(info.transitive_sources)
            if hasattr(info, "transitive_pyc_files"):
                transitive.append(info.transitive_pyc_files)
            if hasattr(info, "transitive_pyi_files"):
                transitive.append(info.transitive_pyi_files)
    return depset(transitive = transitive)

def _py_cmk_package_impl(ctx):
    inputs = _collect_inputs(ctx.attr.deps)

    # Flattening the transitive depset to a list is the same time/space tradeoff stock `py_package`
    # makes (see py_package.bzl). It is acceptable here because this rule runs once per wheel.
    in_scope = []
    for f in inputs.to_list():
        owner = f.owner
        if owner == None or owner.workspace_name != "":
            continue
        if _under_root(owner.package, ctx.attr.include_roots):
            in_scope.append(f)

    return [DefaultInfo(files = depset(direct = in_scope))]

py_cmk_package = rule(
    implementation = _py_cmk_package_impl,
    attrs = {
        "deps": attr.label_list(
            providers = [[PyInfo]],
            doc = "Targets to collect filtered sources from.",
        ),
        "include_roots": attr.string_list(
            doc = "Bazel package paths (e.g. \"cmk\") whose owned files are kept, including subpackages.",
        ),
    },
    doc = "py_package replacement that filters by target package root.",
)
