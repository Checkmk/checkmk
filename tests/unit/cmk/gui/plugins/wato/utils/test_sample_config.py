# Following import is used to trigger plugin loading
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.plugins.wato.utils as utils


def test_registered_generators():
    assert sorted(utils.sample_config_generator_registry.keys()) == sorted([
        'acknowledge_initial_werks',
        'basic_wato_config',
        'cee_agent_bakery',
        'cee_basic_config',
        'create_automation_user',
        'ec_sample_rule_pack',
    ])


def test_get_sorted_generators():
    assert [g.ident() for g in utils.sample_config_generator_registry.get_generators()] == [
        'basic_wato_config',
        'cee_basic_config',
        'cee_agent_bakery',
        'acknowledge_initial_werks',
        'ec_sample_rule_pack',
        'create_automation_user',
    ]
