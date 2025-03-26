load("perl-modules_http.bzl", "PERL_MODULES_LIST_1", "PERL_MODULES_LIST_2")
load(":rename_perl_packages.bzl", "rename_perl_package")

[rename_perl_package(
    name = module.removesuffix("tar.gz").removesuffix("tgz"),
    srcs = [
        "@" + module + "//file:downloaded",
    ],
    outs = [
        module,
    ],
) for module in PERL_MODULES_LIST_1.keys() + PERL_MODULES_LIST_2.keys()]

filegroup(
    name = "perl_module_list_1",
    srcs = list(PERL_MODULES_LIST_1.keys()),
)

filegroup(
    name = "perl_module_list_2",
    srcs = list(PERL_MODULES_LIST_2.keys()),
)

genrule(
    name = "perl-list-1",
    srcs = PERL_MODULES_LIST_1.keys(),
    outs = ["perl_module_list_1.txt"],
    cmd = """
        echo "$(SRCS)" > $(RULEDIR)/perl_module_list_1.txt
    """,
)

genrule(
    name = "perl-list-2",
    srcs = PERL_MODULES_LIST_2.keys(),
    outs = ["perl_module_list_2.txt"],
    cmd = """
        echo "$(SRCS)" > $(RULEDIR)/perl_module_list_2.txt
    """,
)

genrule(
    name = "perl-modules",
    srcs = [
        "build_module.pl",
        "lib/BuildHelper.pm",
        "perl_module_list_1",
        "perl_module_list_2",
        "perl_module_list_1.txt",
        "perl_module_list_2.txt",
        "@Crypt-SSLeay//:Crypt-SSLeay-0.72.tar.gz",
        "//omd/packages/perl-modules/bin:cpan.wrapper",
        "//omd/packages/perl-modules:MyConfig.pm",
    ],
    outs = [
        "perl-modules.tar",
    ],
    cmd = """
        set -x
        mkdir perl-modules
        export PATH=$$PWD/perl-modules/bin:$$PATH
        export PERL_MM_OPT=INSTALL_BASE=$$PWD/perl-modules
        export PERL_MB_OPT=--install_base=$$PWD/perl-modules
        export MODULEBUILDRC=$$PWD/perl-modules/.modulebuildrc
        export PERL5LIB="$$(dirname $(location @omd_packages//omd/packages/perl-modules:lib/BuildHelper.pm)):$$PWD/perl-modules/lib/perl5:$$PWD/Crypt-SSLeay-0.72"
        FORCE=1 $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $$(cat $(location perl_module_list_1.txt));
        $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $$(cat $(location perl_module_list_2.txt));
        $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $(locations @Crypt-SSLeay//:Crypt-SSLeay-0.72.tar.gz);

        mv perl-modules perl-modules-install
        mkdir -p perl-modules/lib/perl5 perl-modules/bin
        mv perl-modules-install/lib perl-modules/lib/perl5/
        mv perl-modules-install/bin perl-modules/lib/perl5/
        mkdir -p perl-modules/local/lib/perl5
        install -m 755 $(execpath //omd/packages/perl-modules/bin:cpan.wrapper) perl-modules/bin/cpan.wrapper

        # Fixup some library permissions. They need to be owner writable to make
        # dh_strip command of deb packaging procedure work
        find perl-modules/lib/perl5 -type f -name \\*.so -exec chmod u+w {} \\;
        find perl-modules/lib/perl5 -type f -name \\*.pm -exec chmod -x {} \\;
        cd perl-modules/lib/perl5 ; rm -rf utils.pm ; ln -s ../nagios/plugins/utils.pm .; cd -
        mkdir -p perl-modules/lib/perl5/CPAN
        cp $(execpath //omd/packages/perl-modules:MyConfig.pm) perl-modules/lib/perl5/CPAN/MyConfig.skel

        tar cf $@ -C perl-modules .
    """,
    visibility = ["//visibility:public"],
)
