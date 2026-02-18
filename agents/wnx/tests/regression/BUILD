load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "wnx-agent-regression-python-tests",
    srcs = [
        "__init__.py",
        "_test_section_logfiles.py",
        "conftest.py",
        "it_utils.py",
        "local.py",
        "test_agent_start_parameters.py",
        "test_section_check_mk.py",
        "test_section_df.py",
        "test_section_dotnet_clrmemory.py",
        "test_section_eventlog.py",
        "test_section_fileinfo.py",
        "test_section_mem.py",
        "test_section_mrpe.py",
        "test_section_plugin_group.py",
        "test_section_plugin_group_windows_if.py",
        "test_section_ps.py",
        "test_section_services.py",
        "test_section_spool.py",
        "test_section_systemtime.py",
        "test_section_uptime.py",
        "test_section_winperf.py",
        "test_section_wmi_cpuload.py",
        "test_section_wmi_webservices.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)
