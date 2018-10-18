
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
