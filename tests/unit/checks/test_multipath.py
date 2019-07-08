import pytest

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


@pytest.mark.parametrize("group,result", [
    (['iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101', 'dm-7', 'IET,VIRTUAL-DISK'
     ], 'iqn.2015-05.com.oracle:QD_DG_VOTE101_EXAO2ADM1VM101'),
    (['1IET', u'00010001', u'dm-4', u'IET,VIRTUAL-DISK'], '1IET 00010001'),
    (['SDataCoreSANsymphony_DAT05-fscl', u'dm-6', u'DataCore,SANsymphony'
     ], 'SDataCoreSANsymphony_DAT05-fscl'),
    (['SDDN_S2A_9900_1308xxxxxxxx', u'dm-13', u'DDN,S2A', u'9900'], 'SDDN_S2A_9900_1308xxxxxxxx'),
    (['3600508b40006d7da0001a00004740000', u'dm-0', u'HP,HSV210'
     ], '3600508b40006d7da0001a00004740000'),
    (['360080e500017bd72000002eb4c1b1ae8', u'dm-1', u'IBM,1814', u'FAStT'
     ], '360080e500017bd72000002eb4c1b1ae8'),
    (['mpath1', u'(SIBM_____SwapA__________DA02BF71)'], 'SIBM_____SwapA__________DA02BF71'),
    (['anzvol1', '(36005076306ffc6480000000000005005)', 'dm-16', 'IBM,2107900'
     ], '36005076306ffc6480000000000005005'),
    (['1494554000000000052303250303700000000000000000000', 'dm-0', 'IET,VIRTUAL-DISK'
     ], '1494554000000000052303250303700000000000000000000'),
    (['360a980004334644d654a316e65306e51dm-4', u'NETAPP,LUN'], '360a980004334644d654a316e65306e51'),
    (['SFUJITSU_MAW3073NC_DBL2P62003VT'], 'SFUJITSU_MAW3073NC_DBL2P62003VT'),
    (['360a980004334644d654a364469555a76'], '360a980004334644d654a364469555a76'),
    (['orabase.lun50', '(360a9800043346937686f456f59386741)', 'dm-15', 'NETAPP,LUN'
     ], '360a9800043346937686f456f59386741')
])
def test_multipath_parse_groups(check_manager, group, result):
    check = check_manager.get_check("multipath")
    assert result in check.run_parse([group])
