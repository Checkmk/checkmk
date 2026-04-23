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

`gerrit-change-log [<gerrit_url_or_change_number_or_change_id_or_git_ref>]`

The positional argument is optional — pass `HEAD` (or omit / use any git ref)
when the change is the currently checked-out commit. Pass a change number
(e.g. `125896`), a Change-Id (e.g. `Iaa4acff6...`), or a full Gerrit URL
when you want to review a change that is **not** checked out locally.

2. In case a Verified -1 is reported, fetch the Jenkins job results using the jenkins skill
3. For each failed stage, fetch the details of the triggered stage job

# When asked to check out a Gerrit change locally

You can check out a Gerrit change given either its change number
(e.g. `125896`) or its Change-Id (e.g. `Iaa4acff6...`).

1. Make sure the worktree is clean — `git status` must report no uncommitted
   or staged changes. Abort if it is dirty.

2. Ask Gerrit for the ref of the current patch set. `<change>` below is the
   change number or Change-Id provided by the user:

   ```
   ref=$(curl -s --netrc \
     "https://review.lan.tribe29.com/a/changes/<change>?o=CURRENT_REVISION" \
     | sed '1d' \
     | jq -r '.revisions[.current_revision].ref')
   ```

   `ref` will have the form `refs/changes/<NN>/<change_number>/<patchset>`.

3. Fetch that ref from `origin` (already configured in every clone) and
   check it out:

   ```
   git fetch origin "$ref" && git checkout FETCH_HEAD
   ```

   This lands on a detached `FETCH_HEAD`.

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

# When asked to submit a commit chain

Do an rebase on top of the base branch. Select the first change and push it for
review. Wait for the CV job to finish. In case it fails, gather the state from
the jenkins job. Reproduce the issue locally, fix it, verify it locally, then
push for review again. Do this until the CV job finishes successfully. Then
follow the same procedure with the next change. Do this until all changes are
verified by the CV job.
At the end provide a list of changes and a summary of the necessary changes that
each commit needed.

# In case the command gerrit-change-log is missing

Ask the user to clone the zeug_cmk git repository and add it to their PATH.
See also: https://wiki.lan.checkmk.net/x/4zBSCQ
