load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

PERL_MODULES_LIST_1 = {
    "ExtUtils-MakeMaker-7.04.tar.gz": {
        "sha256": "98126b012d70c2af0f8e33a07ebe0d6f2340281b2460981b959a9fb31d5ad97f",
        "url": "https://www.cpan.org/modules/by-module/ExtUtils/ExtUtils-MakeMaker-7.04.tar.gz",
    },
    "parent-0.232.tar.gz": {
        "sha256": "1f8f5c928fd6699a25ead67c23e1159482e7088ce684fbc084b3bcef115e1fc3",
        "url": "https://cpan.metacpan.org/authors/id/C/CO/CORION/parent-0.232.tar.gz",
    },
    "version-0.9924.tar.gz": {
        "sha256": "81e4485ff3faf9b7813584d57b557f4b34e73b6c2eb696394f6deefacf5ca65b",
        "url": "https://www.cpan.org/modules/by-module/version/version-0.9924.tar.gz",
    },
    "Module-CoreList-5.20150420.tar.gz": {
        "sha256": "03768bde1f5c02ba3fc4c093ed58c1c461d1251187b21f2c4ddfffc04b33e686",
        "url": "https://www.cpan.org/modules/by-module/Archive/BINGOS/Module-CoreList-5.20150420.tar.gz",
    },
    "common-sense-3.73.tar.gz": {
        "sha256": "8110c5e472641e0c218f8e023cecc1612ef66f9a1b313261fe219862efe3fd10",
        "url": "https://cpan.metacpan.org/authors/id/M/ML/MLEHMANN/common-sense-3.73.tar.gz",
    },
    "Types-Serialiser-1.0.tar.gz": {
        "sha256": "7ad3347849d8a3da6470135018d6af5fd8e58b4057cd568c3813695f2a04730d",
        "url": "https://src.fedoraproject.org/lookaside/extras/perl-Types-Serialiser/Types-Serialiser-1.0.tar.gz/76460a2bfbc644672499af89192e03fe/Types-Serialiser-1.0.tar.gz",
    },
    "JSON-2.90.tar.gz": {
        "sha256": "4ddbb3cb985a79f69a34e7c26cde1c81120d03487e87366f9a119f90f7bdfe88",
        "url": "https://www.cpan.org/modules/by-module/JSON/JSON-2.90.tar.gz",
    },
    "JSON-PP-2.27300.tar.gz": {
        "sha256": "5feef3067be4acd99ca0ebb29cf1ac1cdb338fe46977585bd1e473ea4bab71a3",
        "url": "https://www.cpan.org/modules/by-module/JSON/JSON-PP-2.27300.tar.gz",
    },
    "JSON-XS-3.01.tar.gz": {
        "sha256": "4e8df3256a5aa9ed304ce1bbcd9140737deef31ba847bff9f4c15480c88c71ab",
        "url": "https://cpan.metacpan.org/authors/id/M/ML/MLEHMANN/JSON-XS-3.01.tar.gz",
    },
}

PERL_MODULES_LIST_2 = {
    "Capture-Tiny-0.27.tar.gz": {
        "sha256": "ba54bc0305eb91ee2b0d769470d6bc62edb5b18d9c75b7ea709ea6b31e9bab21",
        "url": "https://cpan.metacpan.org/authors/id/D/DA/DAGOLDEN/Capture-Tiny-0.27.tar.gz",
    },
    "Carp-Clan-6.04.tar.gz": {
        "sha256": "542e13ece92d40545b8ba6626cfc6ed73071c6cbf6a5537ca126c41b349ae1ec",
        "url": "https://www.cpan.org/modules/by-module/Carp/Carp-Clan-6.04.tar.gz",
    },
    "Class-Accessor-0.34.tar.gz": {
        "sha256": "cdb1e0cdf8380fb9b63b44c33ce5afc1068736d55ac5904bf0eaa1efc1c3cefc",
        "url": "https://www.cpan.org/modules/by-module/App/KASEI/Class-Accessor-0.34.tar.gz",
    },
    "Class-Singleton-1.5.tar.gz": {
        "sha256": "38220d04f02e3a803193c2575a1644cce0b95ad4b95c19eb932b94e2647ef678",
        "url": "https://src.fedoraproject.org/lookaside/extras/perl-Class-Singleton/Class-Singleton-1.5.tar.gz/6a2524f590eda075f4bc929598119241/Class-Singleton-1.5.tar.gz",
    },
    "Config-General-2.56.tar.gz": {
        "sha256": "0996c834ea2ad39ebddda9e59e62d7190ee6f2da3c5d2932c8379c0fa3eafd6b",
        "url": "https://www.cpan.org/modules/by-module/Config/TLINDEN/Config-General-2.56.tar.gz",
    },
    "Crypt-Blowfish_PP-1.12.tar.gz": {
        "sha256": "714f1a3e94f658029d108ca15ed20f0842e73559ae5fc1faee86d4f2195fcf8c",
        "url": "https://www.cpan.org/modules/by-module/PGP/MATTBM/Crypt-Blowfish_PP-1.12.tar.gz",
    },
    "Data-Dumper-2.154.tar.gz": {
        "sha256": "e30fcb6dea290cda85b67fc46d227a2ea890a8bd36c213557adec9c99ebd212f",
        "url": "https://www.cpan.org/modules/by-module/Data/Data-Dumper-2.154.tar.gz",
    },
    "Digest-MD5-2.54.tar.gz": {
        "sha256": "90de11e3743ef1c753a5c2032b434e09472046fbcf346996cbe5d135b217f390",
        "url": "https://www.cpan.org/modules/by-module/Digest/Digest-MD5-2.54.tar.gz",
    },
    "Digest-SHA1-2.13.tar.gz": {
        "sha256": "68c1dac2187421f0eb7abf71452a06f190181b8fc4b28ededf5b90296fb943cc",
        "url": "https://www.cpan.org/modules/by-module/Digest/Digest-SHA1-2.13.tar.gz",
    },
    "ExtUtils-Constant-0.23.tar.gz": {
        "sha256": "23b77025c8a5d3b93c586d4f0e712bcca3ef934edbee00a78c3fad4285f48eab",
        "url": "https://www.cpan.org/modules/by-module/ExtUtils/ExtUtils-Constant-0.23.tar.gz",
    },
    "Getopt-Long-2.43.tar.gz": {
        "sha256": "4abbba65165d1750e5fcb7f3898f3d7315af566a361576426394710b35c2f829",
        "url": "https://archive.netbsd.org/pub/pkgsrc-archive/distfiles/2017Q3/Getopt-Long-2.43.tar.gz",
    },
    "HTTP-Date-6.02.tar.gz": {
        "sha256": "e8b9941da0f9f0c9c01068401a5e81341f0e3707d1c754f8e11f42a7e629e333",
        "url": "https://www.cpan.org/modules/by-module/HTTP/HTTP-Date-6.02.tar.gz",
    },
    "Locale-Maketext-Simple-0.21.tar.gz": {
        "sha256": "b009ff51f4fb108d19961a523e99b4373ccf958d37ca35bf1583215908dca9a9",
        "url": "https://www.cpan.org/authors/id/J/JE/JESSE/Locale-Maketext-Simple-0.21.tar.gz",
    },
    "Math-Calc-Units-1.07.tar.gz": {
        "sha256": "61e3cfdb27bb3bee27beb97124dd930760e1039edc1eb7816c2f5627765f8f8f",
        "url": "https://www.cpan.org/modules/by-module/Parse/SFINK/Math-Calc-Units-1.07.tar.gz",
    },
    "Module-Find-0.12.tar.gz": {
        "sha256": "f490ed1ae2f5c463858fd1383543e2104a0e29706ea53ceda9f55db29b1c83d1",
        "url": "https://www.cpan.org/modules/by-module/Module/Module-Find-0.12.tar.gz",
    },
    "Module-Load-0.32.tar.gz": {
        "sha256": "ae0a6fa0ecb406ac683a00a0adee6af215632778bc81b4f7e44d938936735461",
        "url": "https://www.cpan.org/modules/by-module/Module/Module-Load-0.32.tar.gz",
    },
    "Params-Check-0.38.tar.gz": {
        "sha256": "f0c9d33876c36b1bca1475276d26d2efaf449b256d7cc8118fae012e89a26290",
        "url": "https://www.cpan.org/modules/by-module/Params/Params-Check-0.38.tar.gz",
    },
    "PathTools-3.47.tar.gz": {
        "sha256": "caa8d4b45372b8cb0ef0f6f696efa3a60b0fd394b115cad39a7fbb8f6bd38026",
        "url": "https://www.cpan.org/modules/by-module/Cwd/PathTools-3.47.tar.gz",
    },
    "Scalar-List-Utils-1.42.tar.gz": {
        "sha256": "3507f72541f66a2dce850b9b56771e5fccda3d215c52f74946c6e370c0f4a4da",
        "url": "https://mirror.sobukus.de/files/cpan/Scalar/Scalar-List-Utils-1.42.tar.gz",
    },
    "Sub-Exporter-Progressive-0.001011.tar.gz": {
        "sha256": "0618c6e69c6c0540c41e7560d51981407a6a0768f1330bef6d6ac3c6f1fa7c06",
        "url": "https://www.cpan.org/modules/by-module/Sub/Sub-Exporter-Progressive-0.001011.tar.gz",
    },
    "Sub-Install-0.928.tar.gz": {
        "sha256": "61e567a7679588887b7b86d427bc476ea6d77fffe7e0d17d640f89007d98ef0f",
        "url": "https://www.cpan.org/modules/by-module/Sub/Sub-Install-0.928.tar.gz",
    },
    "Sys-SigAction-0.21.tar.gz": {
        "sha256": "e144207a6fd261eb9f98554c76bea66d95870ee1f62d2d346a1ea95fdccf80db",
        "url": "https://www.cpan.org/modules/by-module/Sys/Sys-SigAction-0.21.tar.gz",
    },
    "Term-ReadLine-Gnu-1.25.tar.gz": {
        "sha256": "22a1b4a156b10dc5e55be5f0030460e62a210f9194e5a469e857e5d17186b003",
        "url": "https://www.cpan.org/modules/by-module/Term/Term-ReadLine-Gnu-1.25.tar.gz",
    },
    "Term-ShellUI-0.92.tar.gz": {
        "sha256": "3279c01c76227335eeff09032a40f4b02b285151b3576c04cacd15be05942bdb",
        "url": "https://www.cpan.org/modules/by-module/Term/Term-ShellUI-0.92.tar.gz",
    },
    "Term-Size-0.207.tar.gz": {
        "sha256": "b04a14b5663b83a49e2516538b5e133409eb38f84ae157b6b200eda595fca21c",
        "url": "https://www.cpan.org/modules/by-module/Term/Term-Size-0.207.tar.gz",
    },
    "TermReadKey-2.37.tar.gz": {
        "sha256": "4a9383cf2e0e0194668fe2bd546e894ffad41d556b41d2f2f577c8db682db241",
        "url": "https://www.cpan.org/modules/by-module/Term/TermReadKey-2.37.tar.gz",
    },
    "Text-ParseWords-3.29.tar.gz": {
        "sha256": "8c45f72afa412d532182963782609517bc42ceb9ccee551aab23459d79959b9a",
        "url": "https://mirrors.ircam.fr/pub/devil-linux/devel/sources/1.6/perl-ext/Text-ParseWords-3.29.tar.gz",
    },
    "Time-HiRes-1.9726.tar.gz": {
        "sha256": "ff662ad9b1f6c75a149db7fa1bfc7a161ac8b271e5f3980345e08b734769109e",
        "url": "https://www.cpan.org/modules/by-module/Time/Time-HiRes-1.9726.tar.gz",
    },
    "Try-Tiny-0.22.tar.gz": {
        "sha256": "60fba46f4693d33d54539104f9001df008dabb400b6837e9605c39a6ee6a1b19",
        "url": "https://src.fedoraproject.org/repo/pkgs/perl-Try-Tiny/Try-Tiny-0.22.tar.gz/6769658bfbca241a470206c9a8819ff2/Try-Tiny-0.22.tar.gz",
    },
    "Perl-OSType-1.008.tar.gz": {
        "sha256": "a1c2cd995314348e04eadb6675943edac55a351e56316cf965ae902e7be0bef1",
        "url": "https://www.cpan.org/modules/by-module/Perl/Perl-OSType-1.008.tar.gz",
    },
    "base-2.18.tar.gz": {
        "sha256": "55b0d21f8edb5ef6dddcb1fd2457acb19c7584f2dfdea614685cd8ea62a1c306",
        "url": "http://mirrors.ibiblio.org/CPAN/modules/by-module/fields/base-2.18.tar.gz",
    },
    "Archive-Zip-1.68.tar.gz": {
        "sha256": "984e185d785baf6129c6e75f8eb44411745ac00bf6122fb1c8e822a3861ec650",
        "url": "https://www.cpan.org/modules/by-module/Archive/Archive-Zip-1.68.tar.gz",
    },
    "HTML-Parser-3.71.tar.gz": {
        "sha256": "be918b3749d3ff93627f72ee4b825683332ecb4c81c67a3a8d72b0435ffbd802",
        "url": "https://www.cpan.org/modules/by-module/URI/GAAS/HTML-Parser-3.71.tar.gz",
    },
    "Term-Clui-1.70.tar.gz": {
        "sha256": "a33ab24dd6ad7874d3488f25c5159afa18f445e186799d233fa419e3a9d728b1",
        "url": "https://www.cpan.org/modules/by-module/Term/PJB/Term-Clui-1.70.tar.gz",
    },
    "URI-1.67.tar.gz": {
        "sha256": "7088d43d5f4902becfa5e0627751f5e6d0e0bdd1637b2d39e70ce807068a274e",
        "url": "https://cpan.metacpan.org/authors/id/E/ET/ETHER/URI-1.67.tar.gz",
    },
    "Class-MethodMaker-2.22.tar.gz": {
        "sha256": "963b01c40653d5e50ec0f03146c72f2bfcc54c3be0bed478ad05e6fffa16182c",
        "url": "https://src.fedoraproject.org/lookaside/pkgs/perl-Class-MethodMaker/Class-MethodMaker-2.22.tar.gz/9f5958706e8d38fa0a04f0e499b6d330/Class-MethodMaker-2.22.tar.gz",
    },
    "HTTP-Message-6.06.tar.gz": {
        "sha256": "087e97009c5239dca4631cf433d836771b3fc5ba5685eef1965f9d3415cbad63",
        "url": "https://www.cpan.org/modules/by-module/LWP/GAAS/HTTP-Message-6.06.tar.gz",
    },
    "Module-Load-Conditional-0.64.tar.gz": {
        "sha256": "06731dc00723c2c74d60b778d345ab22f50ea19b8f0b4023719b2edc08f6e001",
        "url": "https://www.cpan.org/modules/by-module/Module/Module-Load-Conditional-0.64.tar.gz",
    },
    "Net-HTTP-6.07.tar.gz": {
        "sha256": "9f31e0325a5a0930ad309fa019da9d208e57e236fb0598675ed883c820240364",
        "url": "https://www.cpan.org/modules/by-module/XML/MSCHILLI/Net-HTTP-6.07.tar.gz",
    },
    "Term-ProgressBar-2.17.tar.gz": {
        "sha256": "c1e0602c738a91fe54b01bcaa0d1a898b07ef6815c55eb2ebd6da4e3be20f696",
        "url": "https://cpan.metacpan.org/authors/id/S/SZ/SZABGAB/Term-ProgressBar-2.17.tar.gz",
    },
    "Test-Cmd-1.08.tar.gz": {
        "sha256": "f0684168e27a52ca26b35db79c59e7abe9c6e90c87b9109e7e4a03aa0fcca36b",
        "url": "https://cpan.metacpan.org/authors/id/N/NE/NEILB/Test-Cmd-1.08.tar.gz",
    },
    "Test-Simple-1.001014.tar.gz": {
        "sha256": "55a414ce89eb7a5e9e84186f286b002054f10ae8ef4f8f2d61bb710e7549f16b",
        "url": "https://www.cpan.org/modules/by-module/Test/EXODIST/Test-Simple-1.001014.tar.gz",
    },
    "XML-LibXML-2.0134.tar.gz": {
        "sha256": "f0bca4d0c2da35d879fee4cd13f352014186cedab27ab5e191f39b5d7d4f46cf",
        "url": "https://www.cpan.org/modules/by-module/XML/XML-LibXML-2.0134.tar.gz",
    },
    "HTTP-Cookies-6.01.tar.gz": {
        "sha256": "f5d3ade383ce6389d80cb0d0356b643af80435bb036afd8edce335215ec5eb20",
        "url": "https://www.cpan.org/modules/by-module/HTTP/HTTP-Cookies-6.01.tar.gz",
    },
    "IPC-Cmd-0.92.tar.gz": {
        "sha256": "07c59e7f999df620b40bcd5a4b623f4f80a83d701bc93c7b344af50b5a7910eb",
        "url": "https://src.fedoraproject.org/repo/pkgs/perl-IPC-Cmd/IPC-Cmd-0.92.tar.gz/3efb414f6d5d6aecc5b32cd82541895d/IPC-Cmd-0.92.tar.gz",
    },
    "ExtUtils-CBuilder-0.280220.tar.gz": {
        "sha256": "b99b6a3d0bd1d3b2e4809da52835472f4ff149d81f88d9cc55cdeba80e9b80b3",
        "url": "https://mirror.sobukus.de/files/cpan/ExtUtils/ExtUtils-CBuilder-0.280220.tar.gz",
    },
    "ExtUtils-ParseXS-3.24.tar.gz": {
        "sha256": "30b60b8208fc9b7746ed934b678bb9618a8f28994dae8774548353a7b550371e",
        "url": "https://www.cpan.org/modules/by-module/ExtUtils/ExtUtils-ParseXS-3.24.tar.gz",
    },
    "Module-Metadata-1.000027.tar.gz": {
        "sha256": "e2f7dcb48e826d9cb4c08ca8d7e1a1d4ceaa7725f1245eb30c71ecbd119132e7",
        "url": "https://cpan.metacpan.org/authors/id/E/ET/ETHER/Module-Metadata-1.000027.tar.gz",
    },
    "IO-1.25.tar.gz": {
        "sha256": "89790db8b9281235dc995c1a85d532042ff68a90e1504abd39d463f05623e7b5",
        "url": "https://www.cpan.org/modules/by-module/IO/IO-1.25.tar.gz",
    },
    "LWP-Protocol-https-6.10.tar.gz": {
        "sha256": "cecfc31fe2d4fc854cac47fce13d3a502e8fdfe60c5bc1c09535743185f2a86c",
        "url": "https://www.cpan.org/modules/by-module/LWP/LWP-Protocol-https-6.10.tar.gz",
    },
    "List-AllUtils-0.09.tar.gz": {
        "sha256": "4cfe6359cc6c9f4ba0d178e223f4b468d3cf7768d645334962f05de069bdaee2",
        "url": "https://src.fedoraproject.org/lookaside/extras/perl-List-AllUtils/List-AllUtils-0.09.tar.gz/3e2dfeeef80c4e1952443c6b7d48583c/List-AllUtils-0.09.tar.gz",
    },
    "libwww-perl-6.13.tar.gz": {
        "sha256": "5fbd13eebd1933e5a203fceb2c1629efbccff3efc8fab6ec0285c79d0a95f8b2",
        "url": "https://src.fedoraproject.org/repo/pkgs/perl-libwww-perl/libwww-perl-6.13.tar.gz/85b36bcd2fd2450718ee14f894f0d3d1/libwww-perl-6.13.tar.gz",
    },
    "Module-Build-0.4007.tar.gz": {
        "sha256": "15ac5eb06628348391645464840af8ad6f545831a814e2ea502dc89b9fd70152",
        "url": "https://cpan.metacpan.org/authors/id/L/LE/LEONT/Module-Build-0.4007.tar.gz",
    },
    "Module-Runtime-0.014.tar.gz": {
        "sha256": "4c44fe0ea255a9fd00741ee545063f6692d2a28e7ef2fbaad1b24a92803362a4",
        "url": "https://www.cpan.org/modules/by-module/XML/ZEFRAM/Module-Runtime-0.014.tar.gz",
    },
    "YAML-Tiny-1.67.tar.gz": {
        "sha256": "4f54e6e5ae08f0765801e3c3edc44d29a21e54c1789d12b44250cda19aba8d4b",
        "url": "https://mirror.sobukus.de/files/cpan/YAML/YAML-Tiny-1.67.tar.gz",
    },
    "Module-Install-1.16.tar.gz": {
        "sha256": "afac1264255f4d822d44f84df1aa9affad207f9ae805e803d93c845fa120025e",
        "url": "https://cpan.metacpan.org/authors/id/E/ET/ETHER/Module-Install-1.16.tar.gz",
    },
    "XML-NamespaceSupport-1.11.tar.gz": {
        "sha256": "6d8151f0a3f102313d76b64bfd1c2d9ed46bfe63a16f038e7d860fda287b74ea",
        "url": "https://www.cpan.org/modules/by-module/XML/PERIGRIN/XML-NamespaceSupport-1.11.tar.gz",
    },
    "XML-SAX-Base-1.08.tar.gz": {
        "sha256": "666270318b15f88b8427e585198abbc19bc2e6ccb36dc4c0a4f2d9807330219e",
        "url": "https://www.cpan.org/modules/by-module/XML/GRANTM/XML-SAX-Base-1.08.tar.gz",
    },
    "XML-SAX-0.99.tar.gz": {
        "sha256": "32b04b8e36b6cc4cfc486de2d859d87af5386dd930f2383c49347050d6f5ad84",
        "url": "https://www.cpan.org/modules/by-module/XML/GRANTM/XML-SAX-0.99.tar.gz",
    },
    "XML-Simple-2.20.tar.gz": {
        "sha256": "5cff13d0802792da1eb45895ce1be461903d98ec97c9c953bc8406af7294434a",
        "url": "https://src.fedoraproject.org/repo/pkgs/perl-XML-Simple/XML-Simple-2.20.tar.gz/4d10964e123b76eca36678464daa63cd/XML-Simple-2.20.tar.gz",
    },
    "Monitoring-Livestatus-0.74.tar.gz": {
        "sha256": "a07d7c0dc2739cae1e0e4782a0ecffad2ad4f5fe3d4b61f0573ad3fa409cf753",
        "url": "https://www.cpan.org/modules/by-module/Nagios/NIERLEIN/Monitoring-Livestatus-0.74.tar.gz",
    },
    "Params-Util-1.07.tar.gz": {
        "sha256": "30f1ec3f2cf9ff66ae96f973333f23c5f558915bb6266881eac7423f52d7c76c",
        "url": "https://www.cpan.org/modules/by-module/Params/Params-Util-1.07.tar.gz",
    },
    "Path-Class-0.35.tar.gz": {
        "sha256": "9226b305196127d02529303dbd6c37802baafe736f0245cb089241ed25922aee",
        "url": "https://www.cpan.org/modules/by-module/Mail/KWILLIAMS/Path-Class-0.35.tar.gz",
    },
    "Socket-2.019.tar.gz": {
        "sha256": "0a5188686e6b71ef3464a0d74f18bda62912b8e35aeb714483ab5f0b157a7b5e",
        "url": "https://src.fedoraproject.org/repo/extras/perl-Socket/Socket-2.019.tar.gz/8afec24ac4e084e0da0600c2018ccead/Socket-2.019.tar.gz",
    },
    "XML-Parser-2.44.tar.gz": {
        "sha256": "1ae9d07ee9c35326b3d9aad56eae71a6730a73a116b9fe9e8a4758b7cc033216",
        "url": "https://cpan.metacpan.org/authors/id/T/TO/TODDR/XML-Parser-2.44.tar.gz",
    },
    "XML-Twig-3.52.tar.gz": {
        "sha256": "fef75826c24f2b877d0a0d2645212fc4fb9756ed4d2711614ac15c497e8680ad",
        "url": "https://www.cpan.org/modules/by-module/XML/MIROD/XML-Twig-3.52.tar.gz",
    },
    "Config-Tiny-2.20.tgz": {
        "sha256": "8262168e0bf5eddab342a330d3f78120f6a0e88d3224d881a097c3b0d5592f3f",
        "url": "https://cpan.metacpan.org/authors/id/R/RS/RSAVAGE/Config-Tiny-2.20.tgz",
    },
    "File-SearchPath-0.06.tar.gz": {
        "sha256": "ffd6485d407c4013162ccf026b8120e6da1d94aaf3a47aa767e1b4b7546eb274",
        "url": "https://www.cpan.org/modules/by-module/File/File-SearchPath-0.06.tar.gz",
    },
    "Module-Implementation-0.09.tar.gz": {
        "sha256": "c15f1a12f0c2130c9efff3c2e1afe5887b08ccd033bd132186d1e7d5087fd66d",
        "url": "https://www.cpan.org/modules/by-module/Module/Module-Implementation-0.09.tar.gz",
    },
    "Params-Validate-1.18.tar.gz": {
        "sha256": "b25d2488d326f0cfa303cba7ed64fed9ec698b7bfc5d408f0b71058af39206c1",
        "url": "https://cpan.metacpan.org/modules/by-module/Params/Params-Validate-1.18.tar.gz",
    },
    "DateTime-Locale-0.45.tar.gz": {
        "sha256": "8aa1b8db0baccc26ed88f8976a228d2cdf4f6ed4e10fc88c1501ecd8f3ccaf9c",
        "url": "https://src.fedoraproject.org/lookaside/extras/perl-DateTime-Locale/DateTime-Locale-0.45.tar.gz/8ba6a4b70f8fa7d987529c2e2c708862/DateTime-Locale-0.45.tar.gz",
    },
    "DateTime-TimeZone-1.88.tar.gz": {
        "sha256": "42c40ffdaf379533d34a4d083f8b0027f44c46e63324cbb1d4e291856cf1f9ff",
        "url": "https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/DateTime-TimeZone-1.88.tar.gz",
    },
    "Monitoring-Plugin-0.38.tar.gz": {
        "sha256": "bdf035b4f72e8fc9f67a9ae09080377a30187f10e7e09db0bd6430fe3a5dae87",
        "url": "https://www.cpan.org/modules/by-module/Nagios/NIERLEIN/Monitoring-Plugin-0.38.tar.gz",
    },
    "Nagios-Plugin-0.36.tar.gz": {
        "sha256": "3a40577376f1077eb84aaa9897b6974baed2654bfc705ad4832f47ad486e5429",
        "url": "https://www.cpan.org/modules/by-module/Nagios/Nagios-Plugin-0.36.tar.gz",
    },
    "DateTime-1.18.tar.gz": {
        "sha256": "bada2c9fe3e79429f7c84592d9a9defd3a8c71f7b584389d450aa324340d913a",
        "url": "https://src.fedoraproject.org/repo/pkgs/perl-DateTime/DateTime-1.18.tar.gz/58160bea9744a7bc9d7737f7dad9fa72/DateTime-1.18.tar.gz",
    },
}

PERL_MODULES_LIST = {}
PERL_MODULES_LIST.update(PERL_MODULES_LIST_1)
PERL_MODULES_LIST.update(PERL_MODULES_LIST_2)

def perl_modules():
    for module in PERL_MODULES_LIST.keys():
        http_file(
            name = module,
            urls = [
                UPSTREAM_MIRROR_URL + module,
                PERL_MODULES_LIST.get(module).get("url"),
            ],
            sha256 = PERL_MODULES_LIST.get(module).get("sha256"),
        )
