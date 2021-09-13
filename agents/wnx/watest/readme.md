
Special Testing

Mailslot testing
Used to check, whether our mailslot works correctly depending from admin

Admin mode:

1. watest *run_admin_mailslot*: creates mail slot in admin mode, app should be started as admin
2. watest *test_mailslot*: connects to slot && sends log and exit command 

Legacy mode:

1. watest *run_standard_mailslot*: creates mail slot in standard mode
2. watest *test_mailslot*: connects to slot && sends log and exit command 

*On success 1-st process should be stopped in 1 sec.*
Otherwise 1st will not be stopped.

For Admin mode test must be successful only if test_mailsslot comes from elevated(admin) account
For Legacy mode test must be successful for any account






