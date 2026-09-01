# Running the Oracle Bakery Migration Tool

This is strictly for Checkmk Bakery users. If you are not using the bakery, check [README.md under the **Migration from
the Legacy mk_oracle Plugin** section](README.md#migration-from-the-legacy-mk_oracle-plugin).

When running on a site, you will have the following command available to use:

`cmk-migrate-oracle-rulesets`

This tool is used to convert Oracle bakery rules from the original plugin to the new unified plugin.

Note that it can only be run on a central site. It cannot run on a remote site, because the central site would be the
main authority for the remote site configuration.

No rules are deleted - everything is kept as is, though the state depends on the flags used.

## Arguments

- -h or --help: Display the list of arguments and a brief description of what they do.
- --dry-run: Simulates a migration and prints warnings of any issues.
- --apply: Performs a real migration and creates the unified rules. Each rule is created as disabled by default.
- --enable-migrated-rules:
  - Only works with --apply.
  - It creates the new rules as enabled instead of disabled, but only if the original rule was also enabled.
  - It disables the original rule so that there is no failure during baking (both plugins cannot be enabled at the
    same time).

## Warnings

The warnings displayed are based on known differences with the original plugin and the new one.

Most of them relate to fields which cannot be mapped, these include:

- **sqlnet.ora permission group**
- **Host uses xinetd or systemd**
- **Sqlnet Send timeout**
- **Add pre or postfix to TNSALIASes**
- **ORACLE_HOME to use for remote access**

Other fields have sub-fields which cannot be migrated, which include:

- ts_quotas (under **Sections - data to collect**)
  - This field is unused in the legacy plugin in any case.
- TNS Alias (under **Login Defaults**)
- **Login for ASM** is not supported with any of the following fields:
  - host
  - port
  - wallet

## Usage

`cmk-migrate-oracle-rulesets` by itself prints the command line options.

`cmk-migrate-oracle-rulesets --dry-run` will run the migration and show the warnings for each rule.

Here is the example output of a dry-run with a single empty rule:

    Rule '0c1d64a4-fc7b-46eb-b858-5d1110cf1752' (folder: /)
    - 'Sections' was not configured, so the selection the legacy bakery applied by default has been written out explicitly. The new rule pins that selection instead of deferring to the plugin later.
    - No auth defined in legacy rule. Defaulting to Oracle wallet.

    1 rule(s) processed, 2 total warning(s).

    Dry run only — no rules were written. Re-run with --apply to create them.

`cmk-migrate-oracle-rulesets --apply` will have the same output, sans the "Dry run only" line.

All rules are migrated as disabled by default.

If you have minimal warnings and would prefer to create all the new rules as enabled, use:

`cmk-migrate-oracle-rulesets --apply --enable-migrated-rules`

Any rules that were already migrated will not be migrated again.

Only newly created rules will be migrated if the tool is executed again after a prior run.

Every created rule will have **(Migrated)** in the description to help identify it.

## Workflow

### Path 1

The expected workflow for migration is as follows:

`cmk-migrate-oracle-rulesets --dry-run` to see possible problems.

`cmk-migrate-oracle-rulesets --apply` to migrate all rules to the new plugin.

In the GUI, you then edit the generated rules, enabling them as needed.

The legacy rule corresponding to each new rule has to be disabled to prevent baking errors.

Once you bake and deploy the agent, you can check the services of the relevant hosts to make sure everything works as
expected.

Repeat the process for each rule until everything is all clear.

### Path 2

Say you run `cmk-migrate-oracle-rulesets --dry-run` and there are minimal to no issues.

If you are confident in your setup, you directly run:

`cmk-migrate-oracle-rulesets --apply --enable-migrated-rules`

This makes sure the old rules are disabled and the new rules are enabled, allowing you to bake new agents as needed.

The same verification for services on existing hosts can be done, by baking the new agents and deploying them.
