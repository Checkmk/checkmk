load(":rename_perl_packages.bzl", "rename_perl_package")
load("perl-modules_http.bzl", "PERL_MODULES_LIST_1", "PERL_MODULES_LIST_2")

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
    ],
    outs = [
        "perl-modules",
    ],
    cmd = """
        mkdir perl-modules
        export PATH=$$PWD/perl-modules/bin:$$PATH
        export PERL_MM_OPT=INSTALL_BASE=$$PWD/perl-modules
        export PERL_MB_OPT=--install_base=$$PWD/perl-modules
        export MODULEBUILDRC=$$PWD/perl-modules/.modulebuildrc
        export PERL5LIB="$$(dirname $(location @omd_packages//omd/packages/perl-modules:lib/BuildHelper.pm)):$$PWD/perl-modules/lib/perl5:$$PWD/Crypt-SSLeay-0.72"
        FORCE=1 $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $$(cat $(location perl_module_list_1.txt));
        $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $$(cat $(location perl_module_list_2.txt));
        $(location @omd_packages//omd/packages/perl-modules:build_module.pl) -p $$PWD/perl-modules $(locations @Crypt-SSLeay//:Crypt-SSLeay-0.72.tar.gz);
        mkdir -p $@
        cp -r perl-modules/{bin,lib,man} $@
    """,
)
