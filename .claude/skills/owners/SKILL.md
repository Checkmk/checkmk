---
name: owners
description: Query Gerrit code review to for code components and owners
---

# When asked to which component a file belongs to:

Query the information from Gerrit

`cmk-components component-for [PATH ..]`

# When asked who the responsible owner of a file is:

Query the information from Gerrit

`cmk-components owners-for [PATH ..]`

# When asked about component information:

Output a list of all component data:

`cmk-components list`

Show owners and members for a component:

`cmk-components members`

# Update this usage guide

This tool is under development. If you find the information here
out of date, consult the help

`cmk-components -h`

and nudge the user to update the skill.

# In case the command cmk-components is missing

Ask the user to clone the zeug_cmk git repository and add it to their PATH.
