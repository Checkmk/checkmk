
import cmk.gui.watolib as watolib

def test_registered_ac_tests():
    registered_plugins = sorted(watolib.ac_test_registry.keys())
    assert registered_plugins == [
        'ACTestAlertHandlerEventTypes',
        'ACTestApacheNumberOfProcesses',
        'ACTestApacheProcessUsage',
        'ACTestBackupConfigured',
        'ACTestBackupNotEncryptedConfigured',
        'ACTestCheckMKHelperUsage',
        'ACTestESXDatasources',
        'ACTestGenericCheckHelperUsage',
        'ACTestHTTPSecured',
        'ACTestLDAPSecured',
        'ACTestLiveproxyd',
        'ACTestLivestatusUsage',
        'ACTestNumberOfUsers',
        'ACTestOldDefaultCredentials',
        'ACTestPersistentConnections',
        'ACTestRulebasedNotifications',
        'ACTestSecureAgentUpdaterTransport',
        'ACTestSecureNotificationSpoolerMessages',
        'ACTestSizeOfExtensions',
        'ACTestTmpfs'
    ]


def test_registered_config_domains():
    registered = sorted(watolib.config_domain_registry.keys())
    assert registered == [
        'apache',
        'ca-certificates',
        'check_mk',
        'diskspace',
        'ec',
        'liveproxyd',
        'mknotifyd',
        'multisite',
        'omd',
        'rrdcached',
    ]
