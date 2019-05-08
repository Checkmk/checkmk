import pytest  # type: ignore
from testlib.base import Scenario
import cmk_base.config as config
import cmk_base.check_api as check_api
import cmk_base.check_table as check_table


# TODO: This misses a lot of cases
# - different get_check_table arguments
# - handling of clusters / nodes
@pytest.mark.parametrize(
    "hostname,autochecks,expected_result",
    [
        ("empty-host", [], {}),
        # Skip the autochecks automatically for ping hosts
        ("ping-host", [("smart.temp", "bla", {})], {}),
        ("no-autochecks", [], {
            ('smart.temp', '/dev/sda'): ({
                'levels': (35, 40)
            }, u'Temperature SMART /dev/sda', []),
        }),
        # Static checks overwrite the autocheck definitions
        ("autocheck-overwrite", [
            ('smart.temp', '/dev/sda', {
                "is_autocheck": True
            }),
            ('smart.temp', '/dev/sdb', {
                "is_autocheck": True
            }),
        ], {
            ('smart.temp', '/dev/sda'): ({
                'levels': (35, 40)
            }, u'Temperature SMART /dev/sda', []),
            ('smart.temp', '/dev/sdb'): ({
                'is_autocheck': True
            }, u'Temperature SMART /dev/sdb', []),
        }),
        ("ignore-not-existing-checks", [
            ("bla.blub", "ITEM", {}),
        ], {}),
        ("ignore-disabled-rules", [], {
            ('smart.temp', 'ITEM2'): ({
                'levels': (35, 40)
            }, u'Temperature SMART ITEM2', []),
        }),
        ("static-check-overwrite", [], {
            ('smart.temp', '/dev/sda'): ({
                'levels': (35, 40),
                'rule': 1
            }, u'Temperature SMART /dev/sda', [])
        }),
    ])
def test_get_check_table(monkeypatch, hostname, autochecks, expected_result):
    ts = Scenario().add_host(hostname, tags=["test"])
    ts.add_host("ping-host", tags=["no-agent"])
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                (('smart.temp', '/dev/sda', {}), [], ["no-autochecks", "autocheck-overwrite"]),
                (('blub.bla', 'ITEM', {}), [], ["ignore-not-existing-checks"]),
                (('smart.temp', 'ITEM1', {}), [], ["ignore-disabled-rules"], {
                    "disabled": True
                }),
                (('smart.temp', 'ITEM2', {}), [], ["ignore-disabled-rules"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 1
                }), [], ["static-check-overwrite"]),
                (('smart.temp', '/dev/sda', {
                    "rule": 2
                }), [], ["static-check-overwrite"]),
            ]
        },
    )
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(config_cache, "get_autochecks_of", lambda h: autochecks)

    config.load_checks(check_api.get_check_api_context, ["checks/smart"])
    config.add_wato_static_checks_to_checks()
    config.initialize_check_caches()

    assert check_table.get_check_table(hostname) == expected_result
