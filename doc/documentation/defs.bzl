"""Rules to collect documentation pages from the packages they describe."""

_PackageDocsInfo = provider(
    doc = "The page of a package that the start page lists.",
    fields = {"index": "File"},
)

def _package_docs_impl(ctx):
    return [
        DefaultInfo(files = depset([ctx.file.index] + ctx.files.srcs)),
        _PackageDocsInfo(index = ctx.file.index),
    ]

package_docs = rule(
    implementation = _package_docs_impl,
    doc = "The pages of a package. Only `index` is listed on the start page, it links to the others.",
    attrs = {
        "index": attr.label(allow_single_file = [".rst"], mandatory = True),
        "srcs": attr.label_list(allow_files = True),
    },
)

def _doc_srcs_impl(ctx):
    outs = {}
    for f in ctx.files.srcs:
        if f.owner.package == ctx.label.package:
            path = f.short_path.removeprefix(ctx.label.package + "/")
            out = f
        else:
            # Sphinx only reads files below conf.py. Pages from other packages
            # are placed flat, so that page names and published URLs do not
            # depend on the package a page lives in.
            path = f.basename
            out = ctx.actions.declare_file(path)
            ctx.actions.symlink(output = out, target_file = f)
        if path in outs:
            fail("%s and %s both provide the page %s" % (outs[path].owner, f.owner, path))
        outs[path] = out

    # Not .rst, so that Sphinx does not render it as a page of its own.
    toc = ctx.actions.declare_file("package-pages.inc")
    pages = sorted([t[_PackageDocsInfo].index.basename for t in ctx.attr.srcs if _PackageDocsInfo in t])
    ctx.actions.write(
        toc,
        ".. toctree::\n   :maxdepth: 1\n   :caption: Packages\n\n" +
        "".join(["   %s\n" % p for p in pages]),
    )
    return [DefaultInfo(files = depset(outs.values() + [toc]))]

doc_srcs = rule(
    implementation = _doc_srcs_impl,
    doc = """Collects the pages of this package and, by file name, those of other packages.

    The start page includes package-pages.inc, the toctree of the package_docs in srcs.
    """,
    attrs = {
        "srcs": attr.label_list(allow_files = True, mandatory = True),
    },
)
