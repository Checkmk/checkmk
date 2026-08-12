"""Builds rrdtool's Perl bindings (RRDs and RRDp) with the host Perl and MakeMaker.

Upstream drives this from ``bindings/Makefile.am`` (targets ``perl-shared`` and ``perl-piped``),
which just runs ``perl Makefile.PL && make`` in a scratch directory and then ``make install``.
This rule does the same thing directly, so the autotools build is no longer needed for it.

The bindings need nothing beyond core Perl (DynaLoader, ExtUtils::MakeMaker, ExtUtils::ParseXS)
and librrd -- no CPAN module from @perl-modules.

The output is a *directory* rather than a list of files because the layout is host-dependent:
MakeMaker's ``LIB=`` sets ``INSTALLSITELIB = $LIB`` and ``INSTALLSITEARCH = $LIB/$Config{archname}``,
so the arch-specific files land under e.g. ``x86_64-linux-gnu-thread-multi`` on Debian but
``x86_64-linux-thread-multi`` on el/sles.  Those paths are not knowable at analysis time.  Letting
MakeMaker place the files is also what keeps the layout correct on every distro -- do not hardcode
the arch directory name.
"""

def _rrdtool_perl_bindings_impl(ctx):
    out = ctx.actions.declare_directory(ctx.label.name)

    # cc_shared_library can report more than one output, so pick the .so rather than using
    # allow_single_file.
    sos = [f for f in ctx.files.librrd if f.extension == "so"]
    if len(sos) != 1:
        fail("expected exactly one .so from librrd, got: {}".format([f.path for f in ctx.files.librrd]))
    librrd = sos[0]

    # $LIB for MakeMaker.  The doubled lib/perl5/lib/perl5 is the OMD convention: pnp4nagios is
    # configured with --with-perl_lib_path=__OMD_ROOT__/lib/perl5/lib/perl5, so this path is a
    # runtime contract, not a cosmetic choice.
    lib = "{}/lib/perl5/lib/perl5".format(out.path)

    header_dsts = " ".join([h.path for h in ctx.files.rrd_headers])
    shared_srcs = " ".join([f.path for f in ctx.files.perl_shared_srcs])
    piped_srcs = " ".join([f.path for f in ctx.files.perl_piped_srcs])

    command = """
set -eu
root="$(pwd)"
out="$root/{out}"
lib="$root/{lib}"
stage="$root/{out}.stage"
rm -rf "$stage"
mkdir -p "$stage/src/.libs" "$stage/perl-shared" "$stage/perl-piped" "$stage/man3" "$lib"

# Fake the autotools tree that bindings/Makefile.PL expects via ABS_TOP_{{SRC,BUILD}}DIR:
#   INC    = -I$TOP_BUILDDIR/src -I$TOP_SRCDIR/src
#   LDFROM = $(OBJECT) -L$TOP_BUILDDIR/src/.libs/ -lrrd
for h in {headers}; do cp "$root/$h" "$stage/src/"; done
cp "$root/{librrd}" "$stage/src/.libs/librrd.so"
# Makefile.PL declares `depend => {{'RRDs.c' => "$TOP_BUILDDIR/src/librrd.la"}}`; make needs the
# file to exist, but nothing ever reads it.
: > "$stage/src/librrd.la"

for f in {shared}; do cp "$root/$f" "$stage/perl-shared/"; done
for f in {piped}; do cp "$root/$f" "$stage/perl-piped/"; done

# INSTALL*MAN*DIR is redirected into the scratch tree: MakeMaker would otherwise install man pages
# to /usr/local/man, which is not writable here.  The man pages are not shipped.
build_one() {{
    dir="$1"
    cd "$stage/$dir"
    ABS_TOP_SRCDIR="$stage" ABS_TOP_BUILDDIR="$stage" ABS_SRCDIR="$stage/$dir" \
        perl Makefile.PL \
            LIB="$lib" \
            INSTALLMAN1DIR="$stage/man3" INSTALLMAN3DIR="$stage/man3" \
            INSTALLSITEMAN1DIR="$stage/man3" INSTALLSITEMAN3DIR="$stage/man3" \
            >/dev/null
    make >/dev/null
    make install >/dev/null
    cd "$root"
}}

build_one perl-shared
build_one perl-piped

rm -rf "$stage"
""".format(
        out = out.path,
        lib = lib,
        headers = header_dsts,
        librrd = librrd.path,
        shared = shared_srcs,
        piped = piped_srcs,
    )

    ctx.actions.run_shell(
        outputs = [out],
        inputs = ctx.files.rrd_headers + ctx.files.perl_shared_srcs + ctx.files.perl_piped_srcs + [librrd],
        command = command,
        # perl, make and the tools make shells out to (chmod, cp, ...) come from PATH, which only
        # exists in the action when the default shell env is used.
        use_default_shell_env = True,
        mnemonic = "RrdtoolPerlBindings",
        progress_message = "Building rrdtool Perl bindings for %{label}",
    )
    return [DefaultInfo(files = depset([out]))]

rrdtool_perl_bindings = rule(
    implementation = _rrdtool_perl_bindings_impl,
    attrs = {
        "librrd": attr.label(
            mandatory = True,
            allow_files = True,
            doc = "The shared librrd to link RRDs.so against (dynamically, as upstream does).",
        ),
        "perl_piped_srcs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "bindings/perl-piped sources (Makefile.PL, RRDp.pm).",
        ),
        "perl_shared_srcs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "bindings/perl-shared sources (Makefile.PL, RRDs.pm, RRDs.xs).",
        ),
        "rrd_headers": attr.label_list(
            mandatory = True,
            allow_files = [".h"],
            doc = "src/*.h, copied into the fake top-builddir that Makefile.PL includes from.",
        ),
    },
    doc = "Builds the RRDs (XS) and RRDp (pure Perl) bindings into a lib/perl5/lib/perl5 tree.",
)
