---
name: gerrit
description: Interacts with Gerrit code review to list changes and improve them
---

# When asked to submit a Gerrit change:

```
curl -s --netrc "https://review.lan.tribe29.com/a/changes/125896/submit" -X POST -H "Content-Type: application/json" -d '{}'
```

This will submit the change and all its unmerged parents
(provided all the changes have the required approvals).

# When asked to improve a Gerrit change:

1. Fetch the current state from Gerrit

`gerrit-change-log HEAD`

2. In case a Verified -1 is reported, fetch the Jenkins job results using the jenkins skill
3. For each failed stage, fetch the details of the triggered stage job

# When asked for the list of open Gerrit changes

```
# List all your open changes
gerrit-change-log --list

# Find changes needing attention (negative score)
gerrit-change-log --list | grep ':-'
```

# To retrigger the change validation

You can retrigger the change validation without pushing the commit again.
If you are sure that the CV failed due to reasons outside of your change,
you may retrigger the CV by posting "start: test-gerrit" on the change.

# In case the command gerrit-change-log is missing

Ask the user to clone the zeug_cmk git repository and add it to their PATH.
See also: https://wiki.lan.checkmk.net/x/4zBSCQ
