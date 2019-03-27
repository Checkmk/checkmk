import cmk_base.config as config


def test_precompile_ec_logwatch_settings_no_rules(check_manager, monkeypatch):
    check = check_manager.get_check("logwatch.ec")
    assert check.context["_precompile_ec_logwatch_settings"]("unknown-host", {}, []) == []


def test_precompile_ec_logwatch_settings(check_manager, monkeypatch):
    check = check_manager.get_check("logwatch.ec")

    rules = [
        ({
            'reclassify_patterns': [('C', u'abc', u'xyz')]
        }, [], config.ALL_HOSTS, config.ALL_SERVICES),
        ({
            'reclassify_patterns': [('C', u'abc', u'xyz'), ('C', u'heute', u'heute')]
        }, [], ['~non-existent-.*$'], config.ALL_SERVICES),
        ({
            'reclassify_patterns': [('C', u'nene', u'')]
        }, [], ['nene'], config.ALL_SERVICES),
    ]

    expected_settings = [
        ({
            'reclassify_patterns': [('C', u'abc', u'xyz')]
        }, ['']),
        ({
            'reclassify_patterns': [('C', u'abc', u'xyz'), ('C', u'heute', u'heute')]
        }, ['']),
    ]

    assert check.context["_precompile_ec_logwatch_settings"]("non-existent-testhost", {},
                                                             rules) == expected_settings
