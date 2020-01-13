# -*- encoding: utf-8
# yapf: disable
checkname = 'azure_ad'

info = [
    [u'users_count', u'2'],
    [
        u'ad_connect',
        u'[{"deletedDateTime": null, "privacyProfile": null, "street": null, "countryLetterCode": "DE", "id": "93176ea2-ff16-46e0-b84e-862fba579335", "city": null, "assignedPlans": [{"capabilityStatus": "Enabled", "servicePlanId": "fca3e605-0754-4279-8504-3f1229f29614", "service": "WindowsAzure", "assignedDateTime": "2019-05-03T14:48:51Z"}], "preferredLanguage": "de", "state": null, "securityComplianceNotificationPhones": [], "businessPhones": [], "postalCode": null, "onPremisesLastSyncDateTime": null, "technicalNotificationMails": ["foo@bar.baz"], "verifiedDomains": [{"name": "foobar.onmicrosoft.com", "type": "Managed", "isDefault": true, "capabilities": "Email, OfficeCommunicationsOnline", "isInitial": true}], "onPremisesSyncEnabled": null, "displayName": "Standardverzeichnis", "marketingNotificationEmails": [], "provisionedPlans": [], "createdDateTime": "2018-09-14T12:44:23Z", "country": null, "securityComplianceNotificationMails": []}]'
    ]
]

discovery = {'': [(None, {})], 'sync': []}

checks = {
    '': [(None, {}, [(0, '2 User Accounts', [])])],
}
