# PyPi Mirror

By default our internal Python mirror is used. To use the official Python mirror, please export `USE_EXTERNAL_PIPENV_MIRROR=true`.

# Update internal Mirror

To update the internal mirror, trigger the pip-mirror-update Job in Jenkins.

# Update Pipfile

Update the Pipfile and rebuild the Pipfile.lock by calling `make USE_EXTERNAL_PIPENV_MIRROR=true Pipfile.lock`.
Then commit your changes to Gerrit and comment "start: test-pip-mirror-update" on your Gerrit change.
The Pip Mirror Update Job on Jenkins in the Gerrit folder will be triggered and the mirror updated.
When this Job is green, you can retrigger the previously failed Gerrit Job.
