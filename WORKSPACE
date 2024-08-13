workspace(name = "omd_packages")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//omd/packages/toolchain:fork_cc_toolchain_config.bzl", "fork_cc_toolchain_config")

fork_cc_toolchain_config(
    name = "forked_cc_toolchain_config",
)

register_toolchains("//omd/packages/toolchain:linux_gcc13")

RULES_FOREIGN_CC_VERSION = "0.11.1"

http_archive(
    name = "rules_foreign_cc",
    patch_args = ["-p1"],
    patches = ["//omd/packages/foreign_cc:symlink.patch"],
    sha256 = "4b33d62cf109bcccf286b30ed7121129cc34cf4f4ed9d8a11f38d9108f40ba74",
    strip_prefix = "rules_foreign_cc-" + RULES_FOREIGN_CC_VERSION,
    urls = [
        "https://github.com/bazelbuild/rules_foreign_cc/archive/refs/tags/" + RULES_FOREIGN_CC_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_foreign_cc-" + RULES_FOREIGN_CC_VERSION + ".tar.gz",
    ],
)

load("@rules_foreign_cc//foreign_cc:repositories.bzl", "rules_foreign_cc_dependencies")

rules_foreign_cc_dependencies()

RULES_PKG_VERSION = "0.9.1"

http_archive(
    name = "rules_pkg",
    sha256 = "8f9ee2dc10c1ae514ee599a8b42ed99fa262b757058f65ad3c384289ff70c4b8",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_pkg/releases/download/" + RULES_PKG_VERSION + "/rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
        "https://github.com/bazelbuild/rules_pkg/releases/download/" + RULES_PKG_VERSION + "/rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_pkg-" + RULES_PKG_VERSION + ".tar.gz",
    ],
)

RULES_RUST_VERSION = "0.36.2"

http_archive(
    name = "rules_rust",
    sha256 = "a761d54e49db06f863468e6bba4a13252b1bd499e8f706da65e279b3bcbc5c52",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_rust/releases/download/" + RULES_RUST_VERSION + "/rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
        "https://github.com/bazelbuild/rules_rust/releases/download/" + RULES_RUST_VERSION + "/rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
        UPSTREAM_MIRROR_URL + "rules_rust-v" + RULES_RUST_VERSION + ".tar.gz",
    ],
)

load("//omd/packages/rules:cargo_deps.bzl", "cargo_deps")
load("//omd/packages/rules:rust_workspace.bzl", "rust_workspace")

rust_workspace()

load("@rules_pkg//:deps.bzl", "rules_pkg_dependencies")

rules_pkg_dependencies()

#   .--PACKAGES------------------------------------------------------------.
#   |           ____   _    ____ _  __    _    ____ _____ ____             |
#   |          |  _ \ / \  / ___| |/ /   / \  / ___| ____/ ___|            |
#   |          | |_) / _ \| |   | ' /   / _ \| |  _|  _| \___ \            |
#   |          |  __/ ___ \ |___| . \  / ___ \ |_| | |___ ___) |           |
#   |          |_| /_/   \_\____|_|\_\/_/   \_\____|_____|____/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'
load(
    "//:package_versions.bzl",
    "PYTHON_VERSION",
)

cargo_deps(
    name = "check-cert-deps",
    package = "packages/check-cert",
)

load("@check-cert-deps//:defs.bzl", check_cert_deps = "crate_repositories")

check_cert_deps()

cargo_deps(
    name = "check-http-deps",
    package = "packages/check-http",
)

load("@check-http-deps//:defs.bzl", check_http_deps = "crate_repositories")

check_http_deps()

load("//omd/packages/patch:patch_http.bzl", "patch")

patch(
    sha256 = "8cf86e00ad3aaa6d26aca30640e86b0e3e1f395ed99f189b06d4c9f74bc58a4e",
    version_str = "2.7.6",
)

load("//omd/packages/redis:redis_http.bzl", "redis")

redis(
    sha256 = "5b2b8b7a50111ef395bf1c1d5be11e6e167ac018125055daa8b5c2317ae131ab",
    version_str = "6.2.6",
)

load("//omd/packages/asio:asio_http.bzl", "asio")

asio(
    sha256 = "09b9fe5c670c7bd47c7ee957cd9c184b4c8f0620d5b08b38ce837a24df971bca",
    version_str = "1.24.0-patched",
)

load("//omd/packages/re2:re2_http.bzl", "re2")

re2(
    sha256 = "665b65b6668156db2b46dddd33405cd422bd611352c5052ab3dae6a5fbac5506",
    version_str = "2022-12-01",
)

load("//omd/packages/openssl:openssl_http.bzl", "openssl")

openssl(
    sha256 = "88525753f79d3bec27d2fa7c66aa0b92b3aa9498dafd93d7cfa4b3780cdae313",
    version_str = "3.0.13",
)

load("//omd/packages/xmlsec1:xmlsec1_http.bzl", "xmlsec1")

xmlsec1(
    sha256 = "5f8dfbcb6d1e56bddd0b5ec2e00a3d0ca5342a9f57c24dffde5c796b2be2871c",
    version_str = "1.2.37",
)

load("//omd/packages/heirloom-mailx:heirloom-mailx_http.bzl", "heirloommailx")

heirloommailx(
    sha256 = "015ba4209135867f37a0245d22235a392b8bbed956913286b887c2e2a9a421ad",
    version_str = "12.5",
)

load("//omd/packages/monitoring-plugins:monitoring-plugins_http.bzl", "monitoring_plugins")

monitoring_plugins(
    sha256 = "7023b1dc17626c5115b061e7ce02e06f006e35af92abf473334dffe7ff3c2d6d",
    version_str = "2.3.3",
)

load("//omd/packages/stunnel:stunnel_http.bzl", "stunnel")

stunnel(
    sha256 = "c74c4e15144a3ae34b8b890bb31c909207301490bd1e51bfaaa5ffeb0a994617",
    version_str = "5.63",
)

load("//omd/packages/freetds:freetds_http.bzl", "freetds")

freetds(
    sha256 = "be7c90fc771f30411eff6ae3a0d2e55961f23a950a4d93c44d4c488006e64c70",
    version_str = "0.95.95",
)

load("//omd/packages/heirloom-pkgtools:heirloom-pkgtools_http.bzl", "heirloom_pkgtools")

heirloom_pkgtools(
    sha256 = "aa94d33550847d57c62138cabd0f742d4af2f14aa2bfb9e9d4a9427bf498e6cc",
    version_str = "070227",
)

load("//omd/packages/libgsf:libgsf_http.bzl", "libgsf")

libgsf(
    sha256 = "68bede10037164764992970b4cb57cd6add6986a846d04657af9d5fac774ffde",
    version_str = "1.14.44",
)

load("//omd/packages/lcab:lcab_http.bzl", "lcab")

lcab(
    sha256 = "065f2c1793b65f28471c0f71b7cf120a7064f28d1c44b07cabf49ec0e97f1fc8",
    version_str = "1.0b12",
)

load("//omd/packages/msitools:msitools_http.bzl", "msitools")

msitools(
    sha256 = "152eb4149cb44f178af93d17bbe0921b5312f30fb4780e5be113b35747b5cd2e",
    version_str = "0.94",
)

load("//omd/packages/snap7:snap7_http.bzl", "snap7")

snap7(
    sha256 = "fe137737b432d95553ebe5d5f956f0574c6a80c0aeab7a5262fb36b535df3cf4",
    version_str = "1.4.2",
)

load("//omd/packages/perl-modules:perl-modules_http.bzl", "perl_modules")

perl_modules()

load("//omd/packages/crypt-ssleay:cryptssl_http.bzl", "crypt_ssleay")

crypt_ssleay(
    sha256 = "f5d34f813677829857cf8a0458623db45b4d9c2311daaebe446f9e01afa9ffe8",
    version_str = "0.72",
)

load("//omd/packages/nrpe:nrpe_http.bzl", "nrpe")

nrpe(
    sha256 = "8ad2d1846ab9011fdd2942b8fc0c99dfad9a97e57f4a3e6e394a4ead99c0f1f0",
    version_str = "3.2.1",
)

load("//omd/packages/Python:Python_http.bzl", "python")

python(
    sha256 = "56bfef1fdfc1221ce6720e43a661e3eb41785dd914ce99698d8c7896af4bdaa1",
    version_str = PYTHON_VERSION,
)

load("//omd/packages/pnp4nagios:pnp4nagios_http.bzl", "pnp4nagios")

pnp4nagios(
    sha256 = "ab59a8a02d0f70de3cf89b12fe1e9216e4b1127bc29c04a036cd06dde72ee8fb",
    version_str = "0.6.26",
)

load("//omd/packages/mod_fcgid:mod_fcgid_http.bzl", "mod_fcgid")

mod_fcgid(
    sha256 = "1cbad345e3376b5d7c8f9a62b471edd7fa892695b90b79502f326b4692a679cf",
    version_str = "2.3.9",
)

load("//omd/packages/xinetd:xinetd_http.bzl", "xinetd")

xinetd(
    sha256 = "2baa581010bc70361abdfa37f121e92aeb9c5ce67f9a71913cebd69359cc9654",
    version_str = "2.3.15.4",
)

load("//omd/packages/nagios:nagios_http.bzl", "nagios")

nagios(
    sha256 = "b4323f8c027bf3f409225eeb4f7fb8e55856092ef5f890206fc2983bc75b072e",
    version_str = "3.5.1",
)

load("//omd/packages/python3-modules:create_python_requirements.bzl", "create_python_requirements")

create_python_requirements(
    name = "python_modules",
    # TODO: differentiate between own code and things we get from other omd packages
    ignored_modules = [
        "protobuf",  # don't build with pip -> see protobuf omd packages
        "rrdtool",  # don't build with pip -> see rrdtool omd packages
        "agent-receiver",  # don't build with pip (yet)
        "werks",  # don't build with pip (yet)
        "netapp-ontap",  # their build process is broken, see https://github.com/NetApp/ontap-rest-python/issues/46
    ],
    requirements = "//:Pipfile",
)

load("//omd/packages/mod_wsgi:mod_wsgi_http.bzl", "mod_wsgi")

mod_wsgi(
    sha256 = "ee926a3fd5675890b908ebc23db1f8f7f03dc3459241abdcf35d46c68e1be29b",
    version_str = "4.9.4",
)

load("//omd/packages/net-snmp:net-snmp_http.bzl", "netsnmp")

netsnmp(
    sha256 = "75b59d67e871aaaa31c8cef89ba7d06972782b97736b7e8c3399f36b50a8816f",
    version_str = "5.9.1",
)

load("//omd/packages/robotmk:robotmk_http.bzl", "robotmk")

robotmk(
    sha256 = "5b2a77d803372e0762704607cfd426c4cba894c0ff3ac93bb97ba0baf5e2dabf",
    version_str = "v3.0.0-alpha-5",
)

load("//omd/packages/rrdtool:rrdtool_http.bzl", "rrdtool")

rrdtool(
    sha256 = "a199faeb7eff7cafc46fac253e682d833d08932f3db93a550a4a5af180ca58db",
    version_str = "1.7.2",
)

load("//omd/packages/rrdtool:rrdtool_native.bzl", "rrdtool_native")

rrdtool_native(
    sha256 = "a199faeb7eff7cafc46fac253e682d833d08932f3db93a550a4a5af180ca58db",
    version_str = "1.7.2",
)

load("//omd/packages/glib:glib.bzl", "glibconfig")

glibconfig("glibconfig-default", "/usr/lib/x86_64-linux-gnu/glib-2.0")

glibconfig("glibconfig-centos", "/usr/lib64/glib-2.0")

load("//omd/packages/httplib:httplib_http.bzl", "httplib")

httplib(
    sha256 = "2a4503f9f2015f6878baef54cd94b01849cc3ed19dfe95f2c9775655bea8b73f",
    version_str = "0.13.3",
)

http_archive(
    name = "gtest",
    sha256 = "4911bfedea2a94cbf50ea328b2e9b3bcb0bd03cdc28c3492cc810f77e44b2746",
    strip_prefix = "googletest-57e107a10ea4ff5d8d31df9e4833f80b414b0dd2",
    url = "https://github.com/google/googletest/archive/57e107a10ea4ff5d8d31df9e4833f80b414b0dd2.tar.gz",
)

http_archive(
    name = "rules_cc",
    sha256 = "35f2fb4ea0b3e61ad64a369de284e4fbbdcdba71836a5555abb5e194cf119509",
    strip_prefix = "rules_cc-624b5d59dfb45672d4239422fa1e3de1822ee110",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_cc/archive/624b5d59dfb45672d4239422fa1e3de1822ee110.tar.gz",
        "https://github.com/bazelbuild/rules_cc/archive/624b5d59dfb45672d4239422fa1e3de1822ee110.tar.gz",
    ],
)

load("@rules_cc//cc:repositories.bzl", "rules_cc_dependencies")

rules_cc_dependencies()

http_archive(
    name = "rules_proto",
    sha256 = "6fb6767d1bef535310547e03247f7518b03487740c11b6c6adb7952033fe1295",
    strip_prefix = "rules_proto-6.0.2",
    url = "https://github.com/bazelbuild/rules_proto/releases/download/6.0.2/rules_proto-6.0.2.tar.gz",
)

load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies")

rules_proto_dependencies()

load("@rules_proto//proto:setup.bzl", "rules_proto_setup")

rules_proto_setup()

load("@rules_proto//proto:toolchains.bzl", "rules_proto_toolchains")

rules_proto_toolchains()

http_archive(
    name = "com_google_protobuf",
    sha256 = "76637ddb08533dc6bffbd382e2614b119b8f84d16a025f7516cf2f833d103c12",
    strip_prefix = "protobuf-3d9f7c430a5ae1385512908801492d4421c3cdb7",
    url = "https://github.com/protocolbuffers/protobuf/archive/3d9f7c430a5ae1385512908801492d4421c3cdb7.tar.gz",
)

load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")

protobuf_deps()

load("//omd/packages/redfish_mkp:redfish_mkp_http.bzl", "redfish_mkp")

redfish_mkp(
    commit_hash = "35b0ef91252bbba9b147ec12dc120bcc70bb3cf6",
    sha256 = "c388a2b5525a55a6e0b175c014a3cb375062b4643d2ceed7ee188c054b2f0c8c",
    version_str = "2.3.38",
)

load("//omd/packages/jaeger:jaeger_http.bzl", "jaeger")

jaeger(
    sha256 = "0581d1d3c59ea32d1c3d8a1a6783341ab99a050428abb5d29c717e468680c365",
    version_str = "1.58.1",
)

http_archive(
    name = "bazel_clang_tidy",
    sha256 = "3f31e513bba1cba41ace515c3a0474b7793abc6f10ed5f6e08fa6e6b6d2411b0",
    strip_prefix = "bazel_clang_tidy-bff5c59c843221b05ef0e37cef089ecc9d24e7da",
    url = "https://github.com/erenon/bazel_clang_tidy/archive/bff5c59c843221b05ef0e37cef089ecc9d24e7da.tar.gz",
)

load("//omd/packages/erlang:erlang_http.bzl", "erlang")

erlang(
    version_str = "c1805ad6200cec57bf86640fb9a1c715db515b78",  # This is v26.2.5.2
)

http_archive(
    name = "bazel_iwyu",
    patches = ["//omd/packages/bazel_iwyu:0001-Make-IWYU-executable-configurable.patch"],
    sha256 = "058d2ba699c1a6ef15ffb8b6e98f056250bb6080e634037034099d10bff4d19f",
    strip_prefix = "bazel_iwyu-bb102395e553215abd66603bcdeb6e93c66ca6d7",
    urls = [
        "https://github.com/storypku/bazel_iwyu/archive/bb102395e553215abd66603bcdeb6e93c66ca6d7.tar.gz",
    ],
)
