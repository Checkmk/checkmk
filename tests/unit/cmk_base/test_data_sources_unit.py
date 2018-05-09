import pytest

import cmk_base.data_sources.snmp

def test_data_source_cache_default():
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()


def test_disable_data_source_cache():
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    assert not source.is_agent_cache_disabled()
    source.disable_data_source_cache()
    assert source.is_agent_cache_disabled()


def test_disable_data_source_cache_no_read(mocker):
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.set_max_cachefile_age(999)
    source.disable_data_source_cache()

    import os
    mocker.patch.object(os.path, "exists", return_value=True)

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._read_cache_file() is None
    disabled_checker.assert_called_once()


def test_disable_data_source_cache_no_write(mocker):
    source = cmk_base.data_sources.snmp.SNMPDataSource("hostname", "ipaddress")
    source.disable_data_source_cache()

    disabled_checker = mocker.patch.object(source, "is_agent_cache_disabled")
    assert source._write_cache_file("X") is None
    disabled_checker.assert_called_once()


def test_ds_command_line_expansion_legacy_macros():
    source = cmk_base.data_sources.programs.DSProgramDataSource("hostname", "ipaddress", "echo '<IP> <HOST>'")
    assert source._get_command_line() == "echo 'ipaddress hostname'"


def test_ds_command_line_expansion_host_macros():
    source = cmk_base.data_sources.programs.DSProgramDataSource("hostname", "ipaddress", "echo '$HOSTNAME$'")
    assert source._get_command_line() == "echo 'hostname'"


def test_ds_command_line_expansion_left_over_macros():
    source = cmk_base.data_sources.programs.DSProgramDataSource("hostname", "ipaddress", "echo '$BLABLUB$'")
    assert source._get_command_line() == "echo ''"


def test_ds_command_line_expansion_skip_shell_variables():
    source = cmk_base.data_sources.programs.DSProgramDataSource("hostname", "ipaddress", "echo '$BLABLUB$ $XXX'")
    assert source._get_command_line() == "echo ' $XXX'"
