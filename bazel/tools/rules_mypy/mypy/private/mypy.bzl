# Modified by Checkmk GmbH, see bazel/tools/rules_mypy/VENDORED.md
"""
mypy aspect.

The mypy aspect runs mypy, succeeding if mypy is error free and failing if mypy produces errors. The
result of the aspect is a mypy cache directory, located at [name].mypy_cache. When provided input cache
directories (the results of other mypy builds), the underlying action first attempts to merge the cache
directories.
"""

load("@bazel_features//:features.bzl", "bazel_features")
load("@cmk_requirements//:requirements.bzl", cmk_requirement = "requirement")
load("@mypy_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:py_binary.bzl", "py_binary")
load("@rules_python//python:py_info.bzl", RulesPythonPyInfo = "PyInfo")
load(":py_type_library.bzl", "PyTypeLibraryInfo")

_LegacyPyInfo = bazel_features.globals.PyInfo or RulesPythonPyInfo

MypyCacheInfo = provider(
    doc = "Output details of the mypy build rule.",
    fields = {
        "directory": "Location of the mypy cache produced by this target.",
    },
)

def _extract_import_dir(import_):
    # Remove first parent from the directory
    if "/" in import_:
        # "_main/path/to/package" -> "path/to/package"
        return import_.split("/", 1)[-1]
    else:
        # "_main" -> ""
        return ""

def _imports(target):
    if RulesPythonPyInfo in target:
        return target[RulesPythonPyInfo].imports.to_list()
    elif _LegacyPyInfo in target:
        return target[_LegacyPyInfo].imports.to_list()
    else:
        return []

def _extract_imports(target):
    return [_extract_import_dir(i) for i in _imports(target)]

def _should_ignore_import(imp):
    return "typing-extensions" in imp or "mypy-extensions" in imp or "typing_extensions" in imp or "mypy_extensions" in imp

def _opt_out(opt_out_tags, rule_tags):
    "Returns true iff at least one opt_out_tag appears in rule_tags."
    if len(opt_out_tags) == 0:
        return False

    for tag in opt_out_tags:
        if tag in rule_tags:
            return True

    return False

def _opt_in(opt_in_tags, rule_tags):
    "Returns true iff opt_in_tags is empty or at least one of opt_in_tags appears in rule_tags."
    if len(opt_in_tags) == 0:
        return True

    for tag in opt_in_tags:
        if tag in rule_tags:
            return True

    return False

def _mypy_impl(target, ctx):
    # skip non-root targets
    if target.label.workspace_root != "":
        return []

    if RulesPythonPyInfo not in target and _LegacyPyInfo not in target:
        return []

    # disable if a target is tagged with at least one suppression tag
    if _opt_out(ctx.attr._suppression_tags, ctx.rule.attr.tags):
        return []

    # disable if there are opt-in tags and one is not present
    if not _opt_in(ctx.attr._opt_in_tags, ctx.rule.attr.tags):
        return []

    # ignore rules that don't carry source files like py_proto_library
    if not hasattr(ctx.rule.files, "srcs"):
        return []

    # Exclude non-python sources from custom rules that return PyInfo
    lintable_srcs = [
        s
        for s in ctx.rule.files.srcs
        if "/_virtual_imports/" not in s.short_path and s.extension in ("py", "pyi")
    ]
    if not lintable_srcs:
        return []

    # we need to help mypy map the location of external deps by setting
    # MYPYPATH to include the site-packages directories.
    external_deps = {}

    # we need to help mypy map the location of first party deps with custom
    # 'imports' by setting MYPYPATH.
    imports_dirs = {}

    # generated dirs
    generated_dirs = {}

    upstream_caches = []

    types = []

    depsets = []

    type_mapping = dict(zip([k.label for k in ctx.attr._types_keys], ctx.attr._types_values))
    dep_with_stubs = [_.label.workspace_root + "/site-packages" for _ in ctx.attr._types_keys]
    additional_types = [
        type_mapping[dep.label]
        for dep in ctx.rule.attr.deps
        if dep.label in type_mapping
    ]

    for import_ in _extract_imports(target):
        imports_dirs[import_] = 1

    pyi_files = []
    pyi_dirs = {}
    for dep in (ctx.rule.attr.deps + additional_types):
        if RulesPythonPyInfo in dep and hasattr(dep[RulesPythonPyInfo], "direct_pyi_files"):
            dep_pyi_files = dep[RulesPythonPyInfo].direct_pyi_files.to_list()
            pyi_files.extend(dep_pyi_files)

            # A stub directory for each import root that contains a stub file. The other import
            # roots of the dependency, e.g. those of its own dependencies, hold none of its stubs.
            roots = [imp for imp in _extract_imports(dep) if imp != "site-packages"]
            for pyi_file in dep_pyi_files:
                for root in roots:
                    if root == "" or pyi_file.short_path.startswith(root + "/"):
                        pyi_dirs["%s/%s" % (ctx.bin_dir.path, root)] = None
        depsets.append(dep.default_runfiles.files)
        if PyTypeLibraryInfo in dep:
            types.append(dep[PyTypeLibraryInfo].directory.path + "/site-packages")
        elif dep.label in type_mapping:
            continue
        elif dep.label.workspace_root.startswith("external/"):
            # TODO: do we need this, still?
            external_deps[dep.label.workspace_root + "/site-packages"] = 1
            for imp in _imports(dep):
                path = "external/{}".format(imp)
                if path not in dep_with_stubs:
                    external_deps[path] = 1
        elif dep.label.workspace_name == "":
            for import_ in _extract_imports(dep):
                imports_dirs[import_] = 1

        if MypyCacheInfo in dep:
            upstream_caches.append(dep[MypyCacheInfo].directory)

        for file in dep.default_runfiles.files.to_list():
            root = file.root.path
            if root:
                if dep.label.workspace_root.startswith("external/"):
                    generated_dirs[root + "/" + dep.label.workspace_root] = 1
                else:
                    generated_dirs[root] = 1

        # TODO: can we use `ctx.bin_dir.path` here to cover generated files
        # and as a way to skip iterating over depset contents to find generated
        # file roots?

    generated_dirs[ctx.bin_dir.path] = 1
    generated_imports_dirs = []
    for generated_dir in generated_dirs.keys():
        for import_ in imports_dirs.keys():
            generated_imports_dirs.append("{}/{}".format(generated_dir, import_))

    path_components = (
        # normally, mypy looks in the current directory last, but we explicitly want
        # to check the current directory first, to avoid issues where mypy finds the
        # output bin_dir from `generated_dirs` first
        # https://github.com/theoremlp/rules_mypy/issues/88
        ["."] +
        # types need to appear first in the mypy path since the module directories
        # are the same and mypy resolves the first ones, first.
        sorted(types) +
        sorted(external_deps) +
        sorted(imports_dirs) +
        # After the source directories, so that output directories can't shadow source
        # packages, but before the generated files, so that stubs win over the generated
        # modules they describe, even when both live in different directories. In reverse
        # order, so that each stub directory comes before its ancestors, which can hold
        # generated modules, too.
        sorted(pyi_dirs, reverse = True) +
        sorted(generated_dirs) +
        sorted(generated_imports_dirs)
    )

    mypy_path = ctx.configuration.host_path_separator.join([x for x in path_components if not _should_ignore_import(x)])

    output_file = ctx.actions.declare_file(ctx.rule.attr.name + ".mypy_stdout")

    args = ctx.actions.args()
    args.add("--output", output_file)

    result_info = [OutputGroupInfo(mypy = depset([output_file]))]
    if ctx.attr.cache:
        cache_directory = ctx.actions.declare_directory(ctx.rule.attr.name + ".mypy_cache")
        args.add("--cache-dir", cache_directory.path)

        outputs = [output_file, cache_directory]
        result_info.append(MypyCacheInfo(directory = cache_directory))
    else:
        outputs = [output_file]

    args.add_all([c.path for c in upstream_caches], before_each = "--upstream-cache")
    args.add_all(lintable_srcs)

    if hasattr(ctx.attr, "_mypy_ini"):
        args.add("--mypy-ini", ctx.file._mypy_ini.path)
        config_files = [ctx.file._mypy_ini]
    else:
        config_files = []

    extra_env = {"PYTHONNOUSERSITE": "true"}
    if ctx.attr.color:
        # force color on
        extra_env["MYPY_FORCE_COLOR"] = "1"

        # force color on only works if TERM is set to something that supports color
        extra_env["TERM"] = "xterm-256color"

    py_type_files = [x for x in ctx.rule.files.data if x.basename == "py.typed" or x.extension == "pyi"]
    ctx.actions.run(
        mnemonic = "mypy",
        progress_message = "mypy %{label}",
        inputs = depset(
            direct = ctx.rule.files.srcs + py_type_files + pyi_files + upstream_caches + config_files,
            transitive = depsets,
        ),
        outputs = outputs,
        executable = ctx.executable._mypy_cli,
        arguments = [args],
        env = {"MYPYPATH": mypy_path} | ctx.configuration.default_shell_env | extra_env,
    )

    return result_info

def mypy(
        mypy_cli = None,
        mypy_ini = None,
        types = None,
        cache = True,
        color = True,
        suppression_tags = None,
        opt_in_tags = None):
    """
    Create a mypy target inferring upstream caches from deps.

    Args:
        mypy_cli:   (optional) a replacement mypy_cli to use (recommended to produce
                    with mypy_cli macro)
        mypy_ini:   (optional) mypy_ini file to use
        types:      (optional) a dict of dependency label to types dependency label
                    example:
                    ```
                    {
                        requirement("cachetools"): requirement("types-cachetools"),
                    }
                    ```
                    Use the types extension to create this map for a requirements.in
                    or requirements.txt file.
        cache:      (optional, default True) propagate the mypy cache
        color:      (optional, default True) use color in mypy output
        suppression_tags: (optional, default ["no-mypy"]) tags that suppress running
                    mypy on a particular target.
        opt_in_tags: (optional, default []) tags that must be present for mypy to run
                    on a particular target. When specified, this ruleset will _only_
                    run on targets with this tag.

    Returns:
        a mypy aspect.
    """
    types = types or {}

    additional_attrs = {}

    return aspect(
        implementation = _mypy_impl,
        attr_aspects = ["deps"],
        attrs = {
            "cache": attr.bool(default = cache),
            "color": attr.bool(default = color),
            "_mypy_cli": attr.label(
                default = mypy_cli or "//bazel/tools/rules_mypy/mypy/private:mypy",
                cfg = "exec",
                executable = True,
            ),
            "_mypy_ini": attr.label(
                # we provide a default here because Bazel won't allow Label attrs
                # that are public, or private attrs that have default values of None
                default = mypy_ini or "//bazel/tools/rules_mypy/mypy/private:default_mypy.ini",
                allow_single_file = True,
                mandatory = False,
            ),
            "_opt_in_tags": attr.string_list(default = opt_in_tags or []),
            "_suppression_tags": attr.string_list(default = suppression_tags or ["no-mypy"]),
            # pass the dict[Label, Label] in parts because Bazel doesn't have
            # this kind of attr to pass naturally
            "_types_keys": attr.label_list(default = types.keys(), cfg = "exec"),
            "_types_values": attr.label_list(default = types.values(), cfg = "exec"),
        } | additional_attrs,
    )

def mypy_cli(name, deps = None, mypy_requirement = None, python_version = None, tags = None, pyc_collection = "inherit"):
    """
    Produce a custom mypy executable for use with the mypy build rule.

    Args:
        name: name of the binary target this macro produces
        deps: (optional) additional dependencies to include (e.g. mypy plugins)
              (note: must match the Python version of py_binary)
              (typing-extensions, which mypy needs, is always included)
        mypy_requirement: (optional) a replacement mypy requirement
              (note: must match the Python version of py_binary)
        python_version: (optional) the python_version to use for this target
              (defaults to the default Python version, the only one of @mypy_requirements)
        tags: (optional) tags to include in the binary target
        pyc_collection: (optional) the pyc_collection of the binary target, e.g. "include_pyc" to
              include the bytecode of mypy and of the other dependencies
    """

    deps = deps or []
    mypy_requirement = mypy_requirement or requirement("mypy")

    # @mypy_requirements leaves typing-extensions out, see //bazel/tools:mypy_requirements
    typing_extensions = cmk_requirement("typing-extensions")
    if typing_extensions not in deps:
        deps = [typing_extensions] + deps

    py_binary(
        name = name,
        srcs = ["//bazel/tools/rules_mypy/mypy/private:mypy_runner.py"],
        main = "//bazel/tools/rules_mypy/mypy/private:mypy_runner.py",
        visibility = ["//visibility:public"],
        deps = [mypy_requirement] + deps,
        python_version = python_version,
        tags = tags,
        pyc_collection = pyc_collection,
    )
