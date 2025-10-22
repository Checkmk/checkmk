Special Testing

Mailslot testing
Used to check, whether our mailslot works correctly depending from admin

Admin mode:

1. watest _run_admin_mailslot_: creates mail slot in admin mode, app should be started as admin
2. watest _test_mailslot_: connects to slot && sends log and exit command

Legacy mode:

1. watest _run_standard_mailslot_: creates mail slot in standard mode
2. watest _test_mailslot_: connects to slot && sends log and exit command

_On success 1-st process should be stopped in 1 sec._
Otherwise 1st will not be stopped.

For Admin mode test must be successful only if test_mailsslot comes from elevated(admin) account
For Legacy mode test must be successful for any account
