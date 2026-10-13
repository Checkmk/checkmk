# cmk-up playbook reference

Taken from cmk-werk-zeug `doc/cmk-up.md` (2026-10-01, cmk-werk-zeug 0.4.8).

## The playbook

`--init` writes this. The live part is two lines; everything below it is the
schema as commented reference.

<!-- prettier-ignore -->
```yaml
sites:
  v300: {}   # the name says the version; host, agent and discovery come along


# Everything below is reference. Uncomment what you need, delete the rest.
# include: [common.yaml]                     # merged in like one more playbook on the
#                                            # command line (relative to this file)
# ----------------------------------------------------------------- versions
# versions:
#   "2.4": {}                                # installed by cmk-dev-install if missing
#   "3.0": {spec: 3.0.0-2026.09.23, edition: pro}   # spec: what to install; else the key
#   recent-master: {spec: "3.0>=2026.09.29"}   # a daily of 3.0 from that date on (> after it):
#                                            # an installed one if new enough, else the newest
#                                            # community|pro|ultimate|ultimatemt|cloud
#   nightly-master: {alias: master, keep_updated: true}   # BRANCH_VERSION of the checkout;
#                                            # outside one an error: give spec: "3.0"
#   own: {local_path: ~/some-checkmk.deb}
#   old: {spec: "2.3", disabled: true}       # disabled: as if the entry was not there
#                                            # (versions, sites and hosts)
#
# ----------------------------------------------------------------- defaults
# defaults:                                  # every key here is also a site key
#   user: cmkadmin
#   secret: cmk
#   url: http://localhost/{site}/check_mk/api/1.0
#   on_conflict: skip                        # skip|fail|overwrite
#   folder: /cmk-up
#   transport: inline                        # inline|dump|custom_check
#   verify_timeout: 180
#   seed: 0                                  # what the generators are seeded with
#
# -------------------------------------------------------------------- sites
# sites:
#   v300:
#     version: "3.0"                         # a versions: key; else read off the name
#     omd_config: {MCP_TRACE_FORWARD: off}
#     remotes: [v300_r1]                     # created on this version and connected
#     disabled: false                        # true: the site is left out
#     global_settings: {debug_log: true}     # written into the site, needs sudo
#     contact_groups: {cg_ops: Operations}
#     roles:
#       viewer: {base: user, alias: Read-only, permissions: {bi.see_all: "yes"}}
#     users:
#       red: {fullname: Red, password: cmk-up-pw-1234, roles: [viewer],
#             contactgroups: [cg_ops], email: red@example.com}
#     rules:                                 # value is repr'd, value_raw goes verbatim
#       - {id: ops, ruleset: host_contactgroups, value: cg_ops}
#       - {id: lvl, ruleset: checkgroup_parameters:filesystem,
#          value_raw: "{'levels': (80.0, 90.0)}"}
#     bi_config:                             # merged into the pack the site ships
#       rules: {host: {aggregation_function: {type: worst, count: 1, restrict_state: 2}}}
#       aggregations: {default_aggregation: {computation_options: {disabled: false}}}
#
# -------------------------------------------------------------------- hosts
#     hosts:
#       h1:                                  # services, a dump and a walk exclude
#         attributes: {alias: First, ipaddress: 127.0.0.1, site: v300_r1}
#         folder: /cmk-up
#         register_agent: true               # the real agent, needs sudo
#         transport: inline                  # dump: one rule per folder, not per host
#         services:
#           - {name: Load, state: OK, summary: fine}
#           - {name: Disk, state: CRIT, summary: 98% used, perfdata: "used=98;80;90;0;100"}
#           - {name: Long, state: WARN, summary: first line, details: "and the rest"}
#           - {name: Derived, state: P, perfdata: "temp=91;80;90"}    # state from levels
#           - {name: Old local, state: WARN, cached: {interval: 300, form: line}}
#           - {name: Heartbeat, state: CRIT, passive: true, freshness: 2}
#           - {name: Unstable, flap: {interval: 60, policy: random, states: [OK, CRIT]}}
#                                              # policy: random|cycle
#       h2: {agent_dump: linux-ps}           # a bare name is looked up in zeug_cmk
#       h3: {snmp_walk: printer-brother-nc340h}       # tags the host snmp / no-agent
#       h6:                                  # a multi-line string is the content itself
#         agent_dump: |                      # (snmp_walk too; !!binary for non-UTF-8)
#           <<<check_mk>>>
#           Version: 2.4.0
#       h4: {shadow: true, services: [{name: Mirror, state: OK}]}   # pushed, not checked
#       h5: {services: [{name: Old, state: WARN, cached: 300}]}
#       h8: {disabled: true, agent_dump: linux-ps}    # left out
#       c1: {nodes: [h1, h2]}                # a cluster; services via rule clustered_services
#       h7: {relations: [{host: h1, direction: parent}]}   # h7 is h1's management board
#                                            # (child: the reverse; expect: refused when
#                                            # Checkmk's relation discovery must say no)
#                                            # cached: N marks the whole section, so
#                                            # every service of that host must say it
#
# --------------------------------------------------------------- generators
#     hosts: |                               # a container may be a Python expression
#       {name: {"services": [{"name": "Load", "state": random_state()}]}
#        for name in random_host_names(25)}
#       # also random_host_name, random_alias, random_address, FlappyService(...)
#       # a top-level `imports: {hg: ./hostgen.py}` (relative to the playbook, or
#       # absolute) adds your own module: hg.names(random, 8)
#
# ------------------------------------------------------------------- phases
# phases:                                    # instead of sites:, an ordered list
#   - name: build
#     description: what this step sets up
#     sites: {v300: {hosts: {h1: {services: [{name: Load, state: OK}]}}}}
#   - name: break
#     actions: [bi_state]                    # reported at the end of the phase
#     sites: {v300: {hosts: {h1: {services: [{name: Load, state: CRIT}]}}}}
```

Top level: `versions`, `defaults`, and exactly one of `sites` or `phases`.
Keys use underscores. Unknown keys are errors that list the known ones.

### Versions and sites

| Key                           | Meaning                                                                                                                                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `versions.<key>.spec`         | what cmk-dev-install installs; default: the key itself (`"2.4"`, `"3.0.0-2026.09.23"`); a date bound `"3.0>=2026.09.29"` / `"3.0>2026.09.29"`, see below                                       |
| `versions.<key>.edition`      | `community`, `pro`, `ultimate`, `ultimatemt`, `cloud`; default `pro`, `cee` below 2.5                                                                                                          |
| `versions.<key>.local_path`   | a `.deb` to install instead of downloading                                                                                                                                                     |
| `versions.<key>.keep_updated` | always install the newest build of this version                                                                                                                                                |
| `versions.<key>.alias`        | a second name a site may use                                                                                                                                                                   |
| `nightly-master`              | a built-in key: without `spec`, the `BRANCH_VERSION` of the `defines.make` of the Checkmk checkout cmk-up runs from - outside one that is an error, so give a `spec` (the shipped examples do) |
| `sites.<name>.version`        | a `versions:` key or alias; default: read off the name                                                                                                                                         |
| `sites.<name>.omd_config`     | `omd config set` pairs applied after creation (YAML booleans become `on`/`off`)                                                                                                                |
| `sites.<name>.remotes`        | remote sites to create on the same version and connect                                                                                                                                         |

How a site finds its version: `keep_updated` always installs. Otherwise the
version a site already runs pins the choice, else the newest installed match,
else an install. A site name like `v240` implies `2.4`. Version keys must be
quoted (`"2.10"` unquoted is the float `2.1` and is refused). An existing site
on a version that does not match is an error with nothing changed: cmk-up
never recreates a site. `keep_updated` never runs `omd update` on an existing
site. A site to be created must use the user `cmkadmin`.

A date bound takes a daily build of the branch from a date on (`>=`) or after it
(`>`); the date may be written `2026.09.29` or `2026-09-29`:

<!-- prettier-ignore -->
```yaml
versions:
  recent-master:
    spec: "3.0>=2026.09.29"
```

An installed daily that meets it is reused (the newest of them); otherwise
cmk-dev-install installs the branch's newest daily (`3.0`), and if even that one is
older, the run stops with "there is no such daily build yet" (the fresh install is
removed again by the revert). The plan says why an installed build does not count
(`3.0.0-2026.09.28.pro is not 3.0>=2026.09.29`). Releases (`3.0.0p1`) carry no date
and never meet a bound; `local_path` and a bound exclude each other.

### Defaults

Every `defaults:` key is also a site key. Built-in values: `user: cmkadmin`,
`secret: cmk`, `url: http://localhost/{site}/check_mk/api/1.0`,
`on_conflict: skip`, `folder: /cmk-up`, `transport: inline`,
`verify_timeout: 180`, `seed: 0`. `verify_timeout` bounds site start,
activation, discovery and the BI state poll.

### Hosts

| Key              | Meaning                                                                                                                            |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `attributes`     | REST host attributes; default `ipaddress: 127.0.0.1`; `site: <remote>` places the host                                             |
| `folder`         | default `/cmk-up` (the site's `folder`)                                                                                            |
| `services`       | faked services, see below                                                                                                          |
| `agent_dump`     | a real agent output; the host gets the `cmk-agent` tag                                                                             |
| `snmp_walk`      | a real walk; tags `tag_agent: no-agent`, `tag_snmp_ds: snmp-v2`, a `usewalk_hosts` rule                                            |
| `transport`      | `inline`, `dump` or `custom_check`, per host                                                                                       |
| `register_agent` | install the machine's agent from the site if missing and register it through cmk-dev-site's `register_host_with_agent`; needs sudo |
| `shadow`         | a CMC shadow host: no REST host, no checks, states pushed                                                                          |
| `relations`      | host relations, see below: `[{host, direction: parent\|child, expect: stored\|refused}]`                                           |

`agent_dump` and `snmp_walk` take a bare name (a glob in zeug_cmk), a path
(anything with a slash), or the content itself: a multi-line string (`|`)
holds the text exactly as the file would, `!!binary` (base64) the raw bytes of
one that is not valid UTF-8. Either way the data is staged into the site with
sudo.

`services`, `agent_dump` and `snmp_walk` exclude each other. A site without
`hosts:` gets one host named after the site on 127.0.0.1 with
`register_agent: true`, plus one per remote with `site: <remote>`. With ten or
more hosts the tool switches to bulk calls (chunks of 500) and bulk discovery.

### Services

| Key                              | Meaning                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `name`                           | no quotes allowed; unique per host                                                                                 |
| `state`                          | `OK` `WARN` `CRIT` `UNKNOWN` (or `WARNING`, `CRITICAL`, `UNKN`, `0`-`3`), or `P`: derived from the perfdata levels |
| `summary`, `details`, `perfdata` | what the local check line carries                                                                                  |
| `cached`                         | `N` seconds (header form) or `{interval: N, form: line}` (line form)                                               |
| `passive`                        | a `custom_checks` rule with freshness instead of a check; `freshness` in minutes, default 1                        |
| `flap`                           | `{interval, policy, states}`: the state moves at runtime, see below                                                |

A flapping service is neither passive nor cached; a passive service is not
cached; `flap` and `state` exclude each other.

**Transports.** `inline` writes one `datasource_programs` rule per host whose
program prints the `<<<local>>>` section (a `python3 -c` program when the host
has flapping or cached services). Above 50 inline hosts a warning suggests
`dump`. `dump` stages an executable file at `var/check_mk/dumps/<host>` and
uses one folder-level rule; it needs sudo. `custom_check` writes one
`custom_checks` rule per service and refuses dumps, walks, state `P` and
`cached`. Passive services are always custom checks, whatever the transport, and
without a command line: that is what makes the core treat them as passive.

**Cached, two forms.** `cached: 300` is the section header
`<<<local:sep(0):cached(start,300)>>>`: the core sees `cached_at`, and because
the cache belongs to the whole section every non-passive service of that host
must carry the same interval. `cached: {interval: 300, form: line}` puts the
marker on the local line instead: the core never sees it, on purpose, and it
mixes freely. The timestamp is the start of the current interval, so the age
saws like a real cache file's. The header form is CMC only; the raw edition
reports `cached_at` as 0.

**Flapping.** Window = unix time // `interval` (seconds). `random` draws a
state per window from seed, name and window; `cycle` goes round robin.
`states` defaults to `[OK, WARN, CRIT]`; repeating a state weights it; `P` is
not allowed. The site's check interval is untouched, so a 60 s fetch can make
a 60 s flap look constant. A flapping service without a summary gets
`flapping (<policy>, every <n>s)`. The same thing as an expression:
`FlappyService(name, interval, policy="random", states=None, summary="", perfdata="-", details="")`.

**Clusters.** `nodes: [h1, h2]` makes a cluster host (REST `collections/clusters`),
created after the plain hosts and discovered after its nodes, deleted before
them. It takes only `attributes` and `folder`: its services come from the
nodes through a `clustered_services` rule (and `clustered_services_configuration`
for the mode), which go into `rules:`. `overwrite` also resets the node list.

**Shadow hosts.** `shadow: true` writes `etc/check_mk/conf.d/cmk-up-shadow.mk`
(`shadow_hosts.update(...)`, the cmcdump format), runs `cmk -O`, and pushes
the declared states with `UPDATE_SHADOW_HOST_STATE` /
`UPDATE_SHADOW_SERVICE_STATE` through `lq`. Services only, with fixed states.

### Dumps and walks

A value with a slash is a path, `~` expanded, relative to the playbook. A bare
name is a glob searched next to the playbook and in `<zeug_root>/agent_output`
or `<zeug_root>/walks`; it must match exactly one file. `zeug_root` is, in
order: `--dump-root` or the config key `dump_root`; the `zeug_cmk` checkout
`use-dump` on the PATH lives in; the nearest ancestor of the playbook, then of
the current directory, that contains `zeug_cmk/agent_output`. Walks are staged at
`var/check_mk/snmpwalks/<host>`, dumps at `var/check_mk/dumps/<host>`; both
need sudo. A file inside a site that the user cannot read is refused with
the copy-out command (`sudo cp -a ... && sudo chown -R "$USER" ...`).

### Generators

Where a container is expected, a string is evaluated **once, at load time**
as a Python expression. Positions: `sites`; per site `hosts`, `roles`,
`contact_groups`, `users`, `rules`, `global_settings`, `bi_config` and its
`packs` / `rules` / `aggregations`; per host `services` and `attributes`; any
string item of a `services` list. Leaf values (summary, alias, `value_raw`)
are never evaluated.

| Namespace                                        | Content                                                                                                                                                        |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| builtins                                         | `abs all any bool dict divmod enumerate filter float format int isinstance len list map max min range repr reversed round sorted str sum tuple zip ValueError` |
| modules                                          | `random` (a seeded `Random`), `math`, `itertools`, `string`                                                                                                    |
| `random_host_name()`, `random_host_names(count)` | prefix-stable names: a smaller count is a prefix of a larger one                                                                                               |
| `random_alias()`                                 | an alias                                                                                                                                                       |
| `random_address()`                               | attributes with an IPv4 or IPv6 edge case that never answers a ping (IPv6 sets `ipv6address` and `tag_address_family: ip-v6-only`)                             |
| `random_state(weights=None)`                     | default weights OK 7, WARN 2, CRIT 1                                                                                                                           |
| `FlappyService(...)`                             | see above                                                                                                                                                      |

Seeding: each section gets `Random(f"{seed}/{site}/{section}")`; the phase is
not part of it. `random_host_names` uses `{seed}/host_names` alone, so the
names are the same in every section. Seed precedence: `--seed`, the site's
`seed`, `defaults.seed`, the config file, `0`. Results are normalised: tuples
become lists, sets are refused (not reproducible), keys must be strings,
anything not JSON-able is an error that names the line. Mappings may also be
written as lists of `{name: ...}` items.

#### Imports

A top-level `imports:` maps an alias to a Python file; every snippet of the
playbook can then call into it:

<!-- prettier-ignore -->
```yaml
imports:
  hg: ./hostgen.py             # relative to the playbook; ~ and absolute paths work too
sites:
  v300:
    hosts: |
      {name: {"services": hg.services(random, 3)} for name in hg.names(random, 8)}
```

The file is a plain module, loaded once per playbook, with full Python
(it is your code, not a snippet). It sees no seed of its own: pass the
snippet's seeded `random` in, and the result stays reproducible. That also
keeps it testable on its own, e.g. with doctests seeded by `random.Random(0)`:
`python3 -m doctest -v hostgen.py`. An alias must be an identifier and may not
hide a snippet name (`random`, `math`, the builtins above, ...). A failure in
the file names it and the line. See the shipped example `cmk-up 10-imports`
(`doc/example-playbooks/10-imports.yaml` and `hostgen.py` in the cmk-werk-zeug
repo).

### Phases

`phases:` is an ordered list instead of `sites:`. Each has `name` (unique),
`description`, `sites` and `actions`. The `sites:` form is one implicit phase
called `main`. The first phase decides versions and site creation. A pause
separates the phases. The only action is `bi_state`: it polls
`aggregation_state` until `verify_timeout`, waiting for the 60 s BI compile
job, and reports the configured aggregation functions and each aggregation's
state.

### Distributed monitoring

`remotes: [name, ...]` on a site. A remote may not be a site of its own, and
only one central may claim it. Remotes share the central's version, are
created before it, and are connected with cmk-dev-site's
`connect_central_to_remote`. Hosts land on a remote through
`attributes: {site: <remote>}`. A connection added to a central that already
existed is journaled and deleted at revert; the certificate stays. `--verify`
checks the connections too.

### Host relations

Checkmk 3.0 (master, the "Relations:" series) relates hosts: so far one kind,
`management` - a management board (`direction: parent`, "is management board of") and
its OS host (`child`). A host lists its relations:

<!-- prettier-ignore -->
```yaml
srv-01-ilo:
  relations: [{host: srv-01, direction: parent}]
srv-02:
  relations: [{host: srv-02-idrac, direction: child, expect: stored}]
```

The public REST API cannot write relations, so cmk-up uses Checkmk's own relation
discovery (Setup > Relation discovery, internal REST API): the hosts get labels
`cmk-up/relation-pair-<n>` (the board's name) and `cmk-up/relation-board-<n>: yes` (on
the board), one scan proposes exactly the declared pairs, and cmk-up accepts those -
everything else the scan proposes is excluded. Rows: `created`, `kept` (already
related), `refused` (Checkmk said no, as `expect: refused` declared) or `failed`.
`--verify` reads the host custom variable `RELATIONS` of both ends.

- Declaring a relation on one end or on both is the same; both ends must agree on
  `expect`.
- Checkmk refuses (so `expect: refused`): two hosts each claiming to be the other's
  board (the discovery sees a conflict and stores neither), and turning around a pair
  that is already related (`stored_otherwise` - it never overwrites).
- Checkmk does not refuse a second board for an OS host.
- Refused at load time, because no scan can propose it: a self link, a host listed as
  both parent and child, a host that is not a plain host of the same site entry.
- A relation to a host that already existed and was `skip`ped is not proposed (its
  labels were not written): `on_conflict: overwrite`.
- Deleting a host drops both halves (Checkmk), so the revert needs no step of its own;
  relations between pre-existing hosts stay, like every changed object.

### BI, rules, global settings

`bi_config` holds `packs`, `rules`, `aggregations`. An object that exists is
deep-merged under `overwrite`, so one key can enable the shipped
`default_aggregation`. A BI key can be changed but never removed.

A rule is `{id, ruleset, value | value_raw, folder, conditions}` with exactly
one of `value` (repr'd) or `value_raw` (verbatim). It is marked
`cmk-up:rule:<id>`.

`global_settings` is merged into `etc/check_mk/conf.d/wato/global.mk`
("# Written by cmk-up"), never truncating it; needs sudo; not restored by
the revert. The GUI's `multisite.d` file is not written.

### Conflicts

`on_conflict` is `skip` (default), `fail` or `overwrite`, set in `defaults:`,
per site, or with `--on-conflict`. Under `overwrite`, marked rules are deleted
and recreated and hosts are moved to their folder; nothing is duplicated.
The error under `fail` names the value and the layer that set it.

## Running it

| Option                                | Does                                                                                                                                                                                       |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `playbook`                            | the YAML file, or the name of a shipped example (`01-minimal`, a unique prefix like `01` does); optional with `--enroll`, `--init` and `--rm`                                              |
| `--only-site SITE`                    | apply this site only; repeatable                                                                                                                                                           |
| `--only-host HOST`                    | apply this host only, the site's other settings still apply; repeatable                                                                                                                    |
| `--skip FEATURE`                      | leave out one kind of thing: `agent`, `bi`, `contact_groups`, `dumps`, `global_settings`, `remotes`, `roles`, `rules`, `shadow`, `users`, `walks`; repeatable, each is reported as skipped |
| `--protect SITE`                      | never stop, remove or re-version this site - not by the revert, not by `--rm`; repeatable                                                                                                  |
| `--log-file FILE`                     | append every line with the wall-clock time, debug lines and request timings included                                                                                                       |
| `--phase NAME`                        | run this phase only; repeatable                                                                                                                                                            |
| `--list-phases`                       | print `name<TAB>sites<TAB>description` and exit; needs no omd                                                                                                                              |
| `--on-conflict {fail,overwrite,skip}` | overrides the playbook                                                                                                                                                                     |
| `--seed VALUE`                        | overrides the playbook's seed                                                                                                                                                              |
| `-n`, `--dry-run`                     | real probes, every write printed as `~`, nothing changed, no pauses, no verify                                                                                                             |
| `--verify-only`                       | no install, create or start; replay the generators and compare                                                                                                                             |
| `--report FILE`                       | the rows (phase, site, kind, ident, action, note) as JSON                                                                                                                                  |
| `--dump-root DIR`                     | the zeug_cmk checkout for bare dump names                                                                                                                                                  |
| `--config FILE`                       | read defaults from FILE instead of `~/.config/cmk-up.toml`                                                                                                                                 |
| `--enroll FILE`                       | write this machine as a playbook; honours `--only-site`, `--user`, `--secret`, `--all`, `-n`                                                                                               |
| `--from-crash SOURCE`                 | with `--enroll`: a crash directory, the support tarball, or a `crash.info`                                                                                                                 |
| `--all`                               | `--enroll`: include what a fresh site ships                                                                                                                                                |
| `--user`, `--secret`                  | `--enroll`: REST credentials for every site, default `cmkadmin` / `cmk`                                                                                                                    |
| `--version`                           | print cmk-werk-zeug's version (`(local checkout)` when run from one) and quit                                                                                                              |
| `--init [FILE]`                       | write a playbook to start from; default `scenario.yaml`                                                                                                                                    |
| `--rm sites\|all`, `--hauweg`         | wipe the machine, see below; `--hauweg` is `--rm=all`                                                                                                                                      |

Switches, each with a `--no-` form (`--keep` / `--no-keep`):

| Switch              | Default | Does                                                                                                                                                              |
| ------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--tui`             | on      | the full-screen UI; needs a terminal on both ends                                                                                                                 |
| `--keep`            | off     | leave versions, sites and objects in place at the end                                                                                                             |
| `--pause`           | on      | wait for a key between phases and once the setup stands                                                                                                           |
| `--verify`          | off     | read everything back after applying                                                                                                                               |
| `--activate`        | on      | activate changes; off also skips discovery and verification                                                                                                       |
| `--discovery`       | on      | discover services on hosts with agent data                                                                                                                        |
| `--purge`           | off     | delete the playbook's host folders before applying (never the root folder)                                                                                        |
| `--logs`            | off     | plain mode: tail the sites' logs into the output                                                                                                                  |
| `--privileged`      | on      | do what needs root; `--no-privileged` skips installs, site creation, remotes, dumps, walks, shadow hosts, global settings and agents, and reports each as skipped |
| `--foreign-changes` | on      | activate other users' pending changes too; without it such an activation is refused                                                                               |
| `--restore-moves`   | off     | move pre-existing hosts that `overwrite` put into another folder back at the end                                                                                  |
| `--alert`           | on      | terminal bell and desktop notification (`notify-send`) whenever the run waits for you: a pause, the sudo password, the end                                        |
| `--verbose`, `-v`   | off     | log every request                                                                                                                                                 |

`--enroll`, `--init` and `--rm` do not go together; `--from-crash` needs
`--enroll`. `--list-phases`, `--enroll`, `--init` and a `--rm` without a
playbook are always plain. Without a terminal the UI is skipped with a warning.

**Exit codes.** 0 ok; 1 playbook or arguments (also a written playbook that
does not load back); 2 site (does not answer, authentication, omd missing,
version mismatch, `--rm` survivors); 3 apply failed or a conflict under
`fail`; 4 verification failed; 130 interrupted.

**`--enroll FILE --from-crash SOURCE`** builds the playbook from a Checkmk
crash report instead: a crash directory
(`var/check_mk/crashes/<type>/<uuid>/`), the tarball packed for support, or a
`crash.info`. Only `crash.info`, `agent_output` and `snmp_info` are
unpacked (by name, next to the tarball, 256 MiB each at most; an empty member
counts as missing). The site is named `crash_<first 8 characters of the id>`
and runs the report's core (`omd_config: {CORE: ...}`). The header states the
tier:

| Tier | Meaning                                                                                                                                                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | a reproduction: the agent data is in the report (`agent_output` holding the crashing section → `agent_dump:`, or `snmp_info` in walk format → `snmp_walk:`)                                                                                                                                                                    |
| 2    | a likely reproduction: the crashing section is rebuilt from the string table the report kept (`section`, `section_content`, or the locals `info` / `string_table`) as `<<<section>>>` agent output, appended to `agent_output` when that lacks it (piggyback, special agent); SNMP sections delivered that way are best effort |
| 3    | the report keeps only the parsed section: the host comes up without it, the parsed section is written for reading                                                                                                                                                                                                              |
| 4    | GUI, JavaScript, REST API crashes: the site, the user, the request; a crash while saving a rule also brings the rule (`ruleset` = `varname`, its folder, the explicit hosts as condition and as hosts, the value from the locals)                                                                                              |
| 5    | the version and the exception; this crash type carries no reproducible state                                                                                                                                                                                                                                                   |

Files the playbook needs are written next to it as `<playbook stem>.<host>.agent_output`
(and `<stem>.<host>.section.txt` for reading), referenced as `./...`; `-n`
prints the playbook and writes none of them. The header also carries the
exception, the full traceback (`local override` marks frames under `local/`),
version, edition, core, OS and Python, the crash time and the original site,
host, service, item and plugin, the page URL, method, referer and user agent
for GUI crashes, every other report field under "Also in the report", and the
crash.checkmk.com link. After the YAML, commented out: the recorded check
parameters as a `rules:` example with `checkgroup_parameters:TODO` (the
ruleset is not in the report), a `special_agents:<name>` rule for a special
agent crash, the innermost frame's locals, and a GUI request's form
variables. A path inside a site the user cannot read is refused
with the copy-out command; nothing is read through sudo.
