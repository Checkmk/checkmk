"""vue-tsc runs of vue_library projects, which see linked vue packages only through their declarations.

We cannot use ts_project with vue-tsc as `tsc`: it declares one output per
TypeScript source, so vue-tsc's `.vue.d.ts` would be dropped. A project here
emits a directory instead. An npm link carries the sources the bundles need, so the
generated tsconfig maps each linked package to its declarations via `paths`.
"""

load("@aspect_rules_js//js:providers.bzl", "JsInfo")
load("@aspect_rules_js//npm:providers.bzl", "NpmPackageStoreInfo")
load("@bazel_skylib//lib:paths.bzl", "paths")

_VueTsconfigInfo = provider(
    doc = "Makes the js_library whose `srcs` carry it a vue-tsc project.",
    fields = {"tsconfig": "File: the project's tsconfig"},
)

_VueTscInfo = provider(
    doc = "What vue-tsc reads for a target.",
    fields = {
        "exports": "_VueTscInfo that a link to this project passes on, or None",
        "files": "depset of the sources, types and configs of the target and its deps, up to npm links",
        "linked": "depset of the files of linked vue packages: declarations, types and configs",
        "npm_sources": "depset of the files of other npm packages",
        "package": "[declarations dir, package dir] of a project that emits declarations, or None",
        "packages": "dict of the linked vue packages: npm name -> [declarations dir, package dir]",
        "report": "struct of the vue-tsc run's `exit_code`, `log` and `stderr`, or None",
    },
)

def _info(files = depset(), linked = depset(), npm_sources = depset(), package = None, packages = {}, exports = None, report = None):
    return _VueTscInfo(
        exports = exports,
        files = files,
        linked = linked,
        npm_sources = npm_sources,
        package = package,
        packages = packages,
        report = report,
    )

def _merge(own, infos):
    packages = {}
    for info in infos:
        packages.update(info.packages)
    return _info(
        files = depset(transitive = [own] + [info.files for info in infos]),
        linked = depset(transitive = [info.linked for info in infos]),
        npm_sources = depset(transitive = [info.npm_sources for info in infos]),
        packages = packages,
    )

def _run_vue_tsc(ctx, tsconfig, info, out_dir):
    prefix = ctx.label.name + "_vue_tsc"
    inputs = depset(transitive = [info.files, info.linked])
    generated = ctx.actions.declare_file(prefix + ".json")
    ctx.actions.run(
        executable = ctx.executable._generator,
        arguments = [tsconfig.short_path, generated.short_path, json.encode(info.packages)],
        inputs = [f for f in inputs.to_list() if f.extension == "json"],
        outputs = [generated],
        env = {"BAZEL_BINDIR": ctx.bin_dir.path},
        mnemonic = "VueTscConfig",
    )

    report = struct(
        exit_code = ctx.actions.declare_file(prefix + ".exit_code"),
        log = ctx.actions.declare_file(prefix + ".log"),
        stderr = ctx.actions.declare_file(prefix + ".stderr"),
    )
    arguments = [
        "-p",
        paths.basename(generated.short_path),
        "--noEmit",
        "false" if out_dir else "true",
    ]
    outputs = [report.exit_code, report.log, report.stderr]
    if out_dir:
        arguments += [
            "--declaration",
            "--emitDeclarationOnly",
            "--removeComments",
            "--stableTypeOrdering",
            "--rootDir",
            ".",
            "--outDir",
            paths.basename(out_dir.short_path),
        ]
        outputs.append(out_dir)
    ctx.actions.run(
        executable = ctx.executable._vue_tsc_run,
        arguments = [report.exit_code.path, ctx.executable._vue_tsc.path] + arguments,
        inputs = depset([generated], transitive = [inputs, info.npm_sources]),
        outputs = outputs,
        tools = [ctx.attr._vue_tsc[DefaultInfo].files_to_run],
        env = {
            "BAZEL_BINDIR": ctx.bin_dir.path,
            "JS_BINARY__CHDIR": ctx.label.package,
            "JS_BINARY__STDERR_OUTPUT_FILE": report.stderr.path,
            "JS_BINARY__STDOUT_OUTPUT_FILE": report.log.path,
        },
        mnemonic = "VueTsc",
        progress_message = "Type-checking %{label}",
    )
    return report

def _js_library_info(target, ctx):
    own = depset(transitive = [target[JsInfo].sources, target[JsInfo].types])
    info = _merge(own, [dep[_VueTscInfo] for dep in ctx.rule.attr.deps if _VueTscInfo in dep])
    tsconfigs = [src[_VueTsconfigInfo].tsconfig for src in ctx.rule.attr.srcs if _VueTsconfigInfo in src]
    if not tsconfigs:
        return info

    # rules_js links the library named after its package directory into consumers.
    if ctx.label.name != paths.basename(ctx.label.package):
        report = _run_vue_tsc(ctx, tsconfigs[0], info, None)
        exports = None
    else:
        declarations = ctx.actions.declare_directory(ctx.label.name + "_vue_tsc_declarations")
        report = _run_vue_tsc(ctx, tsconfigs[0], info, declarations)
        exports = _info(
            linked = depset([declarations], transitive = [target[JsInfo].types, info.linked]),
            npm_sources = info.npm_sources,
            package = [declarations.short_path, ctx.label.package],
            packages = info.packages,
        )
    return _info(
        files = info.files,
        linked = info.linked,
        npm_sources = info.npm_sources,
        packages = info.packages,
        exports = exports,
        report = report,
    )

def _linked_name(target, ctx):
    if NpmPackageStoreInfo in target:
        return target[NpmPackageStoreInfo].package
    return ctx.rule.attr.package or ctx.rule.attr.src[NpmPackageStoreInfo].package

def _vue_tsc_aspect_impl(target, ctx):
    if JsInfo not in target:
        return []
    if ctx.rule.kind == "js_library":
        return [_js_library_info(target, ctx)]
    src = getattr(ctx.rule.attr, "src", None)
    src_info = src[_VueTscInfo] if type(src) == "Target" and _VueTscInfo in src else None
    if src_info and src_info.report and not src_info.exports:
        fail("{} links {}, which emits no declarations: name it after its package directory".format(target.label, src.label))
    if src_info and src_info.exports:
        exports = src_info.exports
        return [_info(
            linked = exports.linked,
            npm_sources = exports.npm_sources,
            packages = exports.packages | {_linked_name(target, ctx): exports.package},
            exports = exports,
        )]
    return [_info(
        files = depset(transitive = [target[JsInfo].transitive_sources, target[JsInfo].transitive_types]),
        npm_sources = target[JsInfo].npm_sources,
    )]

_vue_tsc_aspect = aspect(
    implementation = _vue_tsc_aspect_impl,
    attr_aspects = ["deps", "src"],
    attrs = {
        "_generator": attr.label(
            default = Label("//bazel/rules:vue_type_check_tsconfig"),
            executable = True,
            cfg = "exec",
        ),
        "_vue_tsc": attr.label(
            default = Label("//bazel/rules:vue_tsc"),
            executable = True,
            cfg = "exec",
        ),
        "_vue_tsc_run": attr.label(
            default = Label("//bazel/rules:vue_tsc_run.sh"),
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
    },
)

def _vue_tsconfig_impl(ctx):
    return [
        DefaultInfo(files = depset([ctx.file.src])),
        _VueTsconfigInfo(tsconfig = ctx.file.src),
    ]

vue_tsconfig = rule(
    doc = "Makes the js_library that lists it in `srcs` a vue-tsc project of `src`.",
    implementation = _vue_tsconfig_impl,
    attrs = {
        "src": attr.label(allow_single_file = [".json"], mandatory = True),
    },
)

def _vue_type_check_impl(ctx):
    report = ctx.attr.project[_VueTscInfo].report
    if not report:
        fail("{} is no vue-tsc project: it lists no vue_tsconfig in `srcs`".format(ctx.attr.project.label))
    passed = ctx.actions.declare_file(ctx.label.name + ".passed")
    ctx.actions.run(
        executable = ctx.executable._report,
        arguments = [report.exit_code.path, report.log.path, report.stderr.path, passed.path],
        inputs = [report.exit_code, report.log, report.stderr],
        outputs = [passed],
        mnemonic = "VueTypeCheck",
        progress_message = "Reporting type errors of %{label}",
    )
    return [OutputGroupInfo(_validation = depset([passed]))]

vue_type_check = rule(
    doc = "Fails the build of this target on a type error found by the vue-tsc run of `project`, but not the build of anything depending on `project`.",
    implementation = _vue_type_check_impl,
    attrs = {
        "project": attr.label(aspects = [_vue_tsc_aspect], mandatory = True, providers = [JsInfo]),
        "_report": attr.label(
            default = Label("//bazel/rules:vue_tsc_report.sh"),
            allow_single_file = True,
            executable = True,
            cfg = "exec",
        ),
    },
)
