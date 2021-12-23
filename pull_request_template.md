Thank you for your interest in contributing to Checkmk!
Unfortunately, due to our current work load, we can at the moment only consider pure bug fixes, as stated in our [Readme](https://github.com/tribe29/checkmk#want-to-contribute).
Thus, any new pull request which is not a pure bug fix will be closed.
Instead of creating a PR, please consider sharing new check plugins, agent plugins, special agents or notification plugins via the [Checkmk Exchange](https://exchange.checkmk.com/).

## General information

Please give a brief summary of the affected device, software or appliance.
Keep in mind that we are experts on monitoring, but we cannot be familiar with all supported devices.
A little context will help us to asses your proposed change.

## Proposed changes

Please give an overview of the issue.
In particular:

+ What is the expected behavior?
+ What is the observed behavior?
+ If it's not obvious from the above: In what way changes your patch the behavior?
+ Is this a new problem? Why are you creating this PR now (new firmware, new device, changed device behavior)?
+ Is there something special about your setup?

## Repro, tests and example data

Sometimes it is hard for us to asses the quality of a fix.
While it may work for you, it is our job to ensure it works for everybody.
These are some ways how to help us (not all of them may be applicable):

+ Can you describe a way to reproduce the problem?
+ Consider writing a unit test that would have failed without your fix
+ Can you share problematic agent output or (sections of) an SNMP walk?
+ Can you submit a crash report and give the ID for reference?

