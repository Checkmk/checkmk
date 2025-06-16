# Testing preparation(Windows)

Import all reg files to the registry.

# How to add new registry for testing

export registry branch from, for example:

```
HKEY_LOCAL_MACHINE\SOFTWARE\ORACLE
```

replace
```
[HKEY_LOCAL_MACHINE\SOFTWARE
```
with
```
[HKEY_LOCAL_MACHINE\SOFTWARE\checkmk\tests\<Repo-Name>\<Package-Name>\<Group-Name>\<Test-Name>
```
where

* Repo-Name is a name of the repo, for example, *2.5.0*
* Package-Name is a name of the package, for example, *mk-oracle* or *cmk-agent-ctl*
* Group-Name is a name of the test group, for example *instances*
* Test-Name is a name of the some test(or tests), for example, *test-registry*

# How to use it

Use pattern custom_branch in code

```
fn read(custom_branch: Optional<None>) ...
```

For example, for mk-sql everything you need  is located in the HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft ...
In This case
standard Branch is "SOFTWARE\"
custom Branch us "SOFTWARE\check\tests\\<Repo-Name>\<Package-Name>\<Group-Name>\<Test-Name>\SOFTWARE\


# Internals

We are using fro production normal Prefix Branch 
**SOFTWARE**  
but for test we are using test Prefix Branch
**SOFTWARE\checkmk\tests\2.5.0\Package-Name\Group-Name\Test-Name**

Data are immutable.

# TODO

1. Move to Integration tests
2. Add deploy mechanic