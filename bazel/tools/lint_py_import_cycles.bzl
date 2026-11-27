"""py-import-cycles linter aspect for aspect_rules_lint framework"""

load("@aspect_rules_lint//lint:defs.bzl", "filter_srcs", "noop_lint_action", "output_files", "should_visit")
load("@rules_python//python:defs.bzl", "PyInfo")

_MNEMONIC = "AspectRulesLintPyImportCycles"

OUTFILE_FORMAT = "{label}.{mnemonic}.{suffix}"

def _resolve_import_root(package, import_rel):
    """Resolve a relative import path against the BUILD file's package.

    Args:
        package: The package path (ctx.label.package), e.g. "cmk" or "packages/cmk-crypto".
        import_rel: A single entry from the imports attribute, e.g. ".", "..", "../foo",
                    or "sub/pkg".

    Returns:
        The resolved module root relative to the workspace root.
    """
    parts = [p for p in package.split("/") if p]
    for component in import_rel.split("/"):
        if component == "" or component == ".":
            pass
        elif component == "..":
            if parts:
                parts = parts[:-1]
        else:
            parts.append(component)
    return "/".join(parts)

def _import_root_of(file, import_roots):
    """The first of the module roots that a source file lies below.

    Args:
        file: A File object whose .path is relative to the execroot.
        import_roots: The resolved module roots (empty for the workspace root).

    Returns:
        The module root, or None if the file lies below none of them.
    """
    for import_root in import_roots:
        if not import_root or file.path.startswith(import_root + "/"):
            return import_root
    return None

def _format_src(file, import_root):
    """Format a source file path as import_root::module_relative_path.

    Args:
        file: A File object whose .path is relative to the execroot.
        import_root: The resolved module root (may be empty for the workspace root).

    Returns:
        A string like "packages/cmk-crypto::cmk/crypto/foo.py" or "::cmk/base/config.py".
    """
    if import_root:
        rel_path = file.path[len(import_root) + 1:]
        return import_root + "::" + rel_path
    return "::" + file.path

def py_import_cycles_action(
        ctx,
        executable,
        options,
        srcs,
        formatted_srcs,
        transitive_srcs,
        human_out,
        machine_out,
        py_import_cycles_runfiles):
    """Run py-import-cycles linter on source files.

    Args:
        ctx: Bazel context
        executable: The py-import-cycles CLI executable
        options: Options to pass to the binary
        srcs: Source files to lint (File objects, used as action inputs)
        formatted_srcs: Source paths formatted as "root::module_path" for the tool
        transitive_srcs: depset of transitive Python sources from dependencies
        human_out: struct for human output
        machine_out: struct for machine output
        py_import_cycles_runfiles: Runfiles of the py-import-cycles binary (includes config files)
    """
    inputs = depset(direct = srcs, transitive = [transitive_srcs] + [py_import_cycles_runfiles])
    args = ctx.actions.args()

    out_folder = ctx.actions.declare_directory(ctx.label.name + "_outputs")
    outputs = [out_folder]
    args.add(out_folder.path, format = "--outputs-folder=%s")
    args.add_all(options)
    args.add("--verbose")
    args.add_all(["--sarif", "{stdout}".format(stdout = machine_out.out.path)])
    outputs.append(machine_out.out)
    args.add("--files")
    args.add_all(formatted_srcs)

    if human_out.exit_code and machine_out.exit_code:
        outputs.extend([human_out.out, human_out.exit_code, machine_out.exit_code])
        command = "{py_import_cycles} $@ > {stdout} 2>&1; echo $? | tee {exit_h} {exit_m} >/dev/null".format(
            py_import_cycles = executable.path,
            stdout = human_out.out.path,
            exit_h = human_out.exit_code.path,
            exit_m = machine_out.exit_code.path,
        )
    else:
        outputs.extend([human_out.out])
        command = "{py_import_cycles} $@ > {stdout} 2>&1".format(
            py_import_cycles = executable.path,
            stdout = human_out.out.path,
        )

    ctx.actions.run_shell(
        command = command,
        inputs = inputs,
        outputs = outputs,
        tools = [executable],
        arguments = [args],
        mnemonic = _MNEMONIC,
        progress_message = "Linting %{label} with py-import-cycles",
    )

def _py_import_cycles_aspect_impl(target, ctx):
    if "no-py-import-cycles" in ctx.rule.attr.tags:
        return []

    if not should_visit(ctx.rule, ctx.attr._rule_kinds, ctx.attr._filegroup_tags):
        return []

    # Following logic copied from `lint/ty.bzl`.
    # Collect transitive sources from dependencies using the standard PyInfo provider.
    transitive_sources = []

    # Collect import paths from PyInfo for third-party dependencies (pip packages).
    # These paths are used with --extra-search-path to help ty find external modules.
    # Import paths from pip packages look like "rules_python~~pip~pip_39_pathspec/site-packages"
    # and need to be prefixed with "external/" to form the actual path in the execroot.
    import_paths = {}

    # Collect from deps attribute using PyInfo
    if hasattr(ctx.rule.attr, "deps"):
        for dep in ctx.rule.attr.deps:
            if PyInfo in dep:
                transitive_sources.append(dep[PyInfo].transitive_sources)
                transitive_sources.append(dep[PyInfo].transitive_pyi_files)

                # Collect imports from pip packages for extra search paths
                for import_path in dep[PyInfo].imports.to_list():
                    if import_path == ctx.workspace_name:
                        continue
                    import_paths["external/" + import_path] = True

    # When srcs contain labels to other targets (e.g., genrules that produce .py files),
    # we need to collect their transitive sources for proper type resolution
    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            if PyInfo in src:
                transitive_sources.append(src[PyInfo].transitive_sources)
                transitive_sources.append(src[PyInfo].transitive_pyi_files)
                for import_path in src[PyInfo].imports.to_list():
                    import_paths["external/" + import_path] = True

    # Compute the module roots from the target's imports attribute so we can
    # pass paths as "root::module_path" to py-import-cycles. Without imports,
    # the BUILD file's directory is the module root.
    import_roots = [
        _resolve_import_root(ctx.label.package, import_rel)
        for import_rel in getattr(ctx.rule.attr, "imports", None) or ["."]
    ]

    # Tests shared from another package lie outside the module roots and have
    # no module path relative to them. A target of their own package checks them.
    py_files = []
    formatted_srcs = []
    for f in filter_srcs(ctx.rule):
        if f.extension != "py":
            continue
        import_root = _import_root_of(f, import_roots)
        if import_root != None:
            py_files.append(f)
            formatted_srcs.append(_format_src(f, import_root))
        elif f.owner.package == ctx.label.package:
            fail("%s lies outside the module roots %s of %s, set by its imports" % (f.path, import_roots, ctx.label))

    outputs, info = output_files(_MNEMONIC, target, ctx)

    if not py_files:
        noop_lint_action(ctx, outputs)
        return [info]

    # Pass transitive sources to py_import_cycles_action so it can resolve imports from dependencies
    transitive_srcs_depset = depset(transitive = transitive_sources)

    py_import_cycles_runfiles = ctx.attr._py_import_cycles_cli[DefaultInfo].default_runfiles.files

    py_import_cycles_action(
        ctx = ctx,
        executable = ctx.executable._py_import_cycles_cli,
        options = ctx.attr._extra_options,
        srcs = py_files,
        formatted_srcs = formatted_srcs,
        transitive_srcs = transitive_srcs_depset,
        human_out = outputs.human,
        machine_out = outputs.machine,
        py_import_cycles_runfiles = py_import_cycles_runfiles,
    )

    return [info]

def lint_py_import_cycles_aspect(
        binary,
        options = [],
        rule_kinds = ["py_binary", "py_library", "py_test"],
        filegroup_tags = ["python", "lint-with-py-import-cycles"]):
    return aspect(
        implementation = _py_import_cycles_aspect_impl,
        attr_aspects = ["deps"],
        attrs = {
            "_extra_options": attr.string_list(
                default = options,
            ),
            "_filegroup_tags": attr.string_list(
                default = filegroup_tags,
            ),
            "_options": attr.label(
                default = "@aspect_rules_lint//lint:options",
            ),
            "_py_import_cycles_cli": attr.label(
                default = binary,
                executable = True,
                cfg = "exec",
            ),
            "_rule_kinds": attr.string_list(
                default = rule_kinds,
            ),
        },
    )
