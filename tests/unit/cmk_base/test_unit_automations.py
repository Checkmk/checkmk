from testlib.base import Scenario

import cmk
import cmk_base.automations
import cmk_base.automations.check_mk as automations
import cmk_base.config as config


def test_registered_automations(site):
    needed_automations = [
        'active-check',
        'analyse-host',
        'analyse-service',
        'delete-hosts',
        'diag-host',
        'get-agent-output',
        'get-check-information',
        'get-check-manpage',
        'get-configuration',
        'get-labels-of',
        'get-real-time-checks',
        'get-service-configurations',
        'inventory',
        'notification-analyse',
        'notification-get-bulks',
        'notification-replay',
        'reload',
        'rename-hosts',
        'restart',
        'scan-parents',
        'set-autochecks',
        'try-inventory',
        'update-dns-cache',
    ]

    if cmk.is_enterprise_edition():
        needed_automations += [
            'bake-agents',
            'get-package-info',
            'get-package',
            'create-package',
            'edit-package',
            'install-package',
            'remove-package',
            'release-package',
            'remove-unpackaged-file',
        ]

    registered_automations = cmk_base.automations.automations._automations.keys()

    assert sorted(needed_automations) == sorted(registered_automations)


def test_get_labels_of_host(monkeypatch):
    automation = automations.AutomationGetLabelsOf()

    ts = Scenario().add_host("test-host")
    ts.set_option("host_labels", {
        "test-host": {
            "explicit": "ding",
        },
    })
    ts.apply(monkeypatch)

    assert automation.execute(["host", "test-host"]) == {
        "labels": {
            "explicit": "ding"
        },
        "label_sources": {
            "explicit": "explicit"
        },
    }


def test_get_labels_of_service(monkeypatch):
    automation = automations.AutomationGetLabelsOf()

    ts = Scenario().add_host("test-host")
    ts.set_ruleset("service_label_rules", [
        ({
            "label1": "val1"
        }, [], config.ALL_HOSTS, ["CPU load$"], {}),
        ({
            "label2": "val2"
        }, [], config.ALL_HOSTS, ["CPU load$"], {}),
    ])
    ts.apply(monkeypatch)

    assert automation.execute(["service", "test-host", "CPU load"]) == {
        "labels": {
            "label1": "val1",
            "label2": "val2"
        },
        "label_sources": {
            "label1": "ruleset",
            "label2": "ruleset"
        }
    }


def test_analyse_host(monkeypatch):
    automation = automations.AutomationAnalyseHost()

    ts = Scenario().add_host("test-host")
    ts.set_option("host_labels", {
        "test-host": {
            "explicit": "ding",
        },
    })
    ts.apply(monkeypatch)

    assert automation.execute(["test-host"]) == {
        "labels": {
            "explicit": "ding"
        },
        "label_sources": {
            "explicit": "explicit"
        },
    }
