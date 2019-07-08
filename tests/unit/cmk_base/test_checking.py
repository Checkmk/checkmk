import pytest
import cmk_base.core
import cmk_base.config
import cmk_base.checking


@pytest.mark.parametrize(
    "rules,active_timeperiods,expected_result",
    [
        # Tuple based
        ((1, 1), ["tp1", "tp2"], (1, 1)),
        (cmk_base.config.TimespecificParamList([(1, 1), (2, 2)]), ["tp1", "tp2"], (1, 1)),
        (cmk_base.config.TimespecificParamList([(1, 1), {
            "tp_default_value": (2, 2),
            "tp_values": []
        }]), ["tp1", "tp2"], (1, 1)),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": []
        }, (1, 1)]), ["tp1", "tp2"], (2, 2)),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (3, 3))]
        }, (1, 1)]), ["tp1", "tp2"], (3, 3)),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp2", (4, 4)), ("tp1", (3, 3))]
        }, (1, 1)]), ["tp1", "tp2"], (4, 4)),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]
        }, (1, 1)]), ["tp2"], (2, 2)),
        (cmk_base.config.TimespecificParamList([(1, 1), {
            "tp_default_value": (2, 2),
            "tp_values": [("tp1", (4, 4)), ("tp3", (3, 3))]
        }]), [], (1, 1)),
        # Dict based
        ({
            1: 1
        }, ["tp1", "tp2"], {
            1: 1
        }),
        (cmk_base.config.TimespecificParamList([{
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1
        }),
        (cmk_base.config.TimespecificParamList([{
            1: 1
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": []
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 2
        }),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 2,
            3: 3
        }),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp1", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 5,
            2: 4,
            3: 6
        }),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp3", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1", "tp2"], {
            1: 1,
            2: 4,
            3: 6
        }),
        (cmk_base.config.TimespecificParamList([{
            "tp_default_value": {
                2: 4
            },
            "tp_values": [("tp3", {
                1: 5
            }), ("tp2", {
                3: 6
            })]
        }, {
            "tp_default_value": {
                2: 2
            },
            "tp_values": [("tp1", {
                3: 3
            })]
        }, {
            1: 1
        }]), ["tp1"], {
            1: 1,
            2: 4,
            3: 3
        }),
    ])
def test_determine_check_parameters(monkeypatch, rules, active_timeperiods, expected_result):
    monkeypatch.setattr(cmk_base.core,
                        "timeperiod_active", lambda tp: _check_timeperiod(tp, active_timeperiods))

    determined_check_params = cmk_base.checking.determine_check_params(rules)
    assert expected_result == determined_check_params,\
           "Determine params: Expected '%s' but got '%s'" % (expected_result, determined_check_params)


def _check_timeperiod(timeperiod, active_timeperiods):
    return timeperiod in active_timeperiods
