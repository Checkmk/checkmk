import cmk
# Following import is used to trigger plugin loading
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.plugins.wato.utils as utils


def test_registered_generators():
    expected_generators = [
        'acknowledge_initial_werks',
        'basic_wato_config',
        'create_automation_user',
        'ec_sample_rule_pack',
    ]

    if not cmk.is_raw_edition():
        expected_generators += [
            'cee_agent_bakery',
            'cee_basic_config',
        ]

    assert sorted(utils.sample_config_generator_registry.keys()) == sorted(expected_generators)


def test_get_sorted_generators():
    expected = [
        'basic_wato_config',
    ]

    if not cmk.is_raw_edition():
        expected += [
            'cee_basic_config',
            'cee_agent_bakery',
        ]

    expected += [
        'acknowledge_initial_werks',
        'ec_sample_rule_pack',
        'create_automation_user',
    ]

    assert [g.ident() for g in utils.sample_config_generator_registry.get_generators()] == expected
