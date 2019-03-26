import cmk_base.automations.check_mk as automations
import cmk_base.config as config


def test_static_check_rules_of_host(monkeypatch):
    as_automation = automations.AutomationAnalyseServices()
    assert as_automation.static_check_rules_of("checkgroup_ding", "test-host") == []

    monkeypatch.setattr(config, "all_hosts", ["test-host"])
    monkeypatch.setattr(config, "host_paths", {"test-host": "/"})
    monkeypatch.setattr(
        config, "static_checks", {
            "checkgroup_ding": [
                (("ding-check", "item"), [], config.ALL_HOSTS, {}),
                (("ding-check", "item2"), [], config.ALL_HOSTS, {
                    "disabled": True
                }),
                (("dong-check", "item2", {
                    "param1": 1
                }), [], config.ALL_HOSTS, {}),
            ],
        })
    config.get_config_cache().initialize()

    assert as_automation.static_check_rules_of("checkgroup_ding", "test-host") == [
        ('ding-check', 'item'),
        ('dong-check', 'item2', {
            'param1': 1
        }),
    ]
