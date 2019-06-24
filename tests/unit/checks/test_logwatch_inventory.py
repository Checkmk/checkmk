import pytest  # type: ignore

from checktestlib import DiscoveryResult, MockHostExtraConf, assertDiscoveryResultsEqual

pytestmark = pytest.mark.checks

INFO1 = [
    ['NODE1', '[[[log1]]]'],
    ['NODE1', '[[[log2]]]'],
    ['NODE1', '[[[log3:missing]]]'],
    ['NODE1', '[[[log4:cannotopen]]]'],
    ['NODE1', '[[[log5]]]'],
    ['NODE2', '[[[log1:missing]]]'],
]


@pytest.mark.parametrize('info, fwd_rule, inventory_groups, expected_result', [
    (INFO1, {}, {}, [('log1', None), ('log2', None), ('log5', None)]),
    (INFO1, [{
        'foo': 'bar'
    }], {}, []),
    (INFO1, [{
        'restrict_logfiles': [u'.*2']
    }], {}, [('log1', None), ('log5', None)]),
    (INFO1, [{}], [[('my_group', ('~log.*', '~.*1'))]], [('log1', None)]),
])
def test_logwatch_inventory_single(check_manager, info, fwd_rule, inventory_groups,
                                   expected_result):
    check = check_manager.get_check('logwatch')

    parsed = check.run_parse(info)

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))


@pytest.mark.parametrize(
    'info, fwd_rule, inventory_groups, expected_result',
    [
        (INFO1, {}, {}, []),
        (INFO1, [{
            'foo': 'bar'
        }], {}, []),
        (INFO1, [{}], [[('my_%s_group', ('~(log)[^5]', '~.*1')),
                        ('my_%s_group', ('~(log).*', '~.*5'))]], [
                            ('my_log_group', {
                                'group_patterns': [('~log.*', '~.*5'), ('~log[^5]', '~.*1')]
                            }),
                        ]),
        (INFO1, [{}], [[('my_group', ('~.*sing', '~.*1'))]], []),  # don't match :missing!
    ])
def test_logwatch_inventory_group(check_manager, info, fwd_rule, inventory_groups, expected_result):
    parsed = check_manager.get_check('logwatch').run_parse(info)

    check = check_manager.get_check('logwatch.groups')

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))


@pytest.mark.parametrize('info, fwd_rule, inventory_groups, expected_result', [
    (INFO1, {}, {}, []),
    (INFO1, [{
        'foo': 'bar'
    }], [{
        'separate_checks': True
    }], [
        ('log1', {
            'expected_logfiles': ['log1']
        }),
        ('log2', {
            'expected_logfiles': ['log2']
        }),
        ('log5', {
            'expected_logfiles': ['log5']
        }),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*']
    }], ["no forwarding"], []),
    (INFO1, [{
        'restrict_logfiles': [u'.*']
    }], [{
        'separate_checks': True
    }], [
        ('log1', {
            'expected_logfiles': ['log1']
        }),
        ('log2', {
            'expected_logfiles': ['log2']
        }),
        ('log5', {
            'expected_logfiles': ['log5']
        }),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*']
    }], [{
        'separate_checks': False
    }], []),
    (INFO1, [{
        'restrict_logfiles': [u'.*']
    }], [{}], []),
    (INFO1, [{
        'restrict_logfiles': [u'log1']
    }], [{
        'separate_checks': True,
        'method': 'pass me on!',
        'facility': 'pass me on!',
        'monitor_logfilelist': 'pass me on!',
        'logwatch_reclassify': 'pass me on!',
        'some_other_key': 'I should be discarded!',
    }], [('log1', {
        'expected_logfiles': ['log1'],
        'method': 'pass me on!',
        'facility': 'pass me on!',
        'monitor_logfilelist': 'pass me on!',
        'logwatch_reclassify': 'pass me on!',
    })]),
])
def test_logwatch_ec_inventory_single(check_manager, info, fwd_rule, inventory_groups,
                                      expected_result):
    parsed = check_manager.get_check('logwatch').run_parse(info)

    check = check_manager.get_check('logwatch.ec_single')

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))


@pytest.mark.parametrize('info, fwd_rule, inventory_groups, expected_result', [
    (INFO1, {}, {}, []),
    (INFO1, [{
        'foo': 'bar'
    }], [{
        'separate_checks': True
    }], []),
    (INFO1, [{
        'foo': 'bar'
    }], [{
        'separate_checks': False
    }], [
        (None, {
            'expected_logfiles': ['log1', 'log2', 'log5']
        }),
    ]),
    (INFO1, [{
        'restrict_logfiles': [u'.*[12]']
    }], [{
        'separate_checks': False
    }], [
        (None, {
            'expected_logfiles': ['log1', 'log2']
        }),
    ]),
])
def test_logwatch_ec_inventory_groups(check_manager, info, fwd_rule, inventory_groups,
                                      expected_result):
    parsed = check_manager.get_check('logwatch').run_parse(info)

    check = check_manager.get_check('logwatch.ec')

    mock_cfgs = [fwd_rule, inventory_groups]

    def mock_cfg(_hostname, _ruleset):
        return mock_cfgs.pop(0)

    with MockHostExtraConf(check, mock_cfg):
        actual_result = DiscoveryResult(check.run_discovery(parsed))
        assertDiscoveryResultsEqual(check, actual_result, DiscoveryResult(expected_result))
