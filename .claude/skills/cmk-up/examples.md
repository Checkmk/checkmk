# Worked examples

## Ticket with phases: SUP-30337

Cluster, BI, and one rule moved from a node to the cluster between phases.
Anchors restate the hosts, `on_conflict: overwrite` makes the restatement converge.

<!-- prettier-ignore -->
```yaml
#!/usr/bin/env -S uvx --from git+ssh://review.lan.tribe29.com:29418/cmk-werk-zeug@main cmk-up
#
# SUP-30337 - the BI special agent is not instantiated for a cluster host
#   cmk-up SUP-30337.yaml --keep
#   cmk-up SUP-30337.yaml --list-phases
#
# phase build:      two MSSQL nodes, cluster mssql-cluster (failover), BI rule and
#                   aggregation "SUP30337 BI Test" on the clustered service
# phase on-node:    BI special agent rule on winmssql-1 -> "Aggr SUP30337 BI Test" there
# phase on-cluster: same rule, condition moved to mssql-cluster -> no Aggr service
#                   anywhere; check with
#                     cmk -D mssql-cluster     (no agent_bi)
#                     cmk -vvI mssql-cluster   (discovers through the nodes)
#
# The BI rule needs the aggregation group to exist, so the special agent rule
# comes one phase after the BI pack.

versions:
  "2.4": {spec: 2.4.0p35}

defaults:
  on_conflict: overwrite   # later phases restate the same hosts and rule

phases:

  - name: build
    description: nodes, cluster, clustered MSSQL service, BI aggregation
    actions: [bi_state]
    sites:
      v240:
        hosts: &hosts
          winmssql-1:   # the active FCI node
            attributes: {tag_agent: all-agents}
            services:
              - {name: MSSQL Connections MSSQLSERVER master, state: OK,
                 summary: "Connections: 12", perfdata: connections=12}
              - {name: Uptime, state: OK, summary: up since 12 days}
          winmssql-2:   # passive node
            attributes: {tag_agent: all-agents}
            services:
              - {name: Uptime, state: OK, summary: up since 12 days}
          mssql-cluster:
            nodes: [winmssql-1, winmssql-2]
            attributes: {tag_agent: all-agents, ipaddress: 127.0.0.2}
        rules:
          - id: mssql-clustered
            ruleset: clustered_services
            value: true
            conditions:
              host_name: {match_on: [winmssql-1, winmssql-2], operator: one_of}
              service_description: {match_on: [.*MSSQL.*], operator: one_of}
          - id: mssql-failover
            ruleset: clustered_services_configuration
            value_raw: "('failover', {})"   # tuples, so value_raw
            conditions:
              host_name: {match_on: [mssql-cluster], operator: one_of}
              service_description: {match_on: [.*MSSQL.*], operator: one_of}
        bi_config:
          packs:
            sup30337: {title: SUP-30337, contact_groups: [], public: true}
          rules:
            sup30337_mssql:
              pack_id: sup30337
              nodes:
                - search: {type: empty}
                  action:
                    type: state_of_service
                    host_regex: mssql-cluster
                    service_regex: MSSQL Connections MSSQLSERVER master
              params: {arguments: []}
              properties:
                title: SUP30337 BI Test
                comment: ""
                docu_url: ""
                icon: ""
                state_messages: {}
              aggregation_function: {type: worst, count: 1, restrict_state: 2}
              computation_options: {disabled: false}
              node_visualization: {type: none, style_config: {}}
          aggregations:
            sup30337_aggr:
              pack_id: sup30337
              comment: ""
              groups: {names: [SUP30337], paths: []}
              node:
                search: {type: empty}
                action: {type: call_a_rule, rule_id: sup30337_mssql, params: {arguments: []}}
              computation_options:
                disabled: false
                use_hard_states: false
                escalate_downtimes_as_warn: false
                freeze_aggregations: false
              aggregation_visualization:
                ignore_rule_styles: false
                layout_id: builtin_default
                line_style: round

  - name: on-node
    description: BI special agent on winmssql-1 - Aggr SUP30337 BI Test appears
    sites:
      v240:
        hosts: *hosts
        rules:
          - &bi_agent
            id: bi-agent
            ruleset: special_agents:bi
            value_raw: >-
              {'options': [{'site': ('local', None),
                            'filter': {'aggr_group_prefix': ['SUP30337']},
                            'assignments': {'querying_host': 'querying_host'}}]}
            conditions:
              host_name: {match_on: [winmssql-1], operator: one_of}

  - name: on-cluster
    description: same rule on mssql-cluster - no agent_bi, no Aggr service
    sites:
      v240:
        hosts: *hosts
        rules:
          - <<: *bi_agent
            conditions:
              host_name: {match_on: [mssql-cluster], operator: one_of}
```

## One host per answer: CMK-38969 (05-reschedule)

No phases; each host shows one case, the comment says what it shows.

<!-- prettier-ignore -->
```yaml
#!/usr/bin/env -S uvx --from "cmk-werk-zeug@latest" cmk-up
#
# hint: to run the development version, change the shebang to
#  #!/usr/bin/env -S uvx --from git+ssh://review.lan.tribe29.com:29418/cmk-werk-zeug@main cmk-up
#
# CMK-38969 / werk 22458 - what "reschedule" means, one host per answer
#   cmk-up doc/example-playbooks/05-reschedule.yaml --keep
# then: Monitor > All hosts > <host> > Services of host, and hover the reschedule icon

sites:

  v300:

    hosts:

      byproduct:   # check_mk-local -> "Reschedule 'Check_MK' service"
        services:
          - {name: Load, state: OK, summary: a byproduct of the agent check}

      cached:      # cached_at set -> greyed out, cache age on hover
        services:
          - {name: Old data, state: WARN, summary: from a cache, cached: 300}

      cached-local:  # the blind spot: a cached *local* check marks the line, not
        services:    # the header, so the core never sees it -> Check_MK redirect
          - name: Old data
            state: WARN
            summary: from a cached local check
            cached: {interval: 300, form: line}

      passive:     # no active check -> greyed out, "checked passively"
        services:
          - {name: Heartbeat, state: CRIT, summary: nothing arrived, passive: true}
          - {name: Plain, state: OK, summary: agent data next to it}

      remote:      # a shadow object -> no reschedule offered at all (CMC only, sudo)
        shadow: true
        attributes: {alias: Mirrored from elsewhere, ipaddress: 10.1.2.3}
        services:
          - {name: Mirror A, state: OK, summary: fine over there}
          - {name: Mirror B, state: CRIT, summary: broken over there}
```

## Generated from a GUI crash (tier 4, unrefined, cmk-werk-zeug 0.4.9)

<!-- prettier-ignore -->
```yaml
#!/usr/bin/env -S uvx --from "cmk-werk-zeug>=0.4.5" cmk-up
#
# cmk-up playbook from crash dcbc2498-4b07-11f1-8eb1-ad93ad433c9a (gui)
# Tier 4: the site, the user and what the request carried; what the page showed is not in a report.
#
# KeyError: 0
#   /omd/sites/checkmk/lib/python3/cmk/gui/sidebar/__init__.py:287 in _initial_config
# Checkmk 2.5.0p1 pro, core cmc, Ubuntu 22.04.5 LTS, Python 3.13.13 (main, Apr 27 2026, 09:37:42) [GCC 14.2.0]
# crashed 2026-05-08 20:00:56 +0200 on site 'checkmk'
# open: /crash_dcbc2498/check_mk/index.py
#   GET, language en, https
#   user agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0
# https://crash.checkmk.com/gui/crashreportview/show/dcbc2498-4b07-11f1-8eb1-ad93ad433c9a
#
# Traceback (most recent call last):
#   lib/python3/cmk/gui/wsgi/applications/checkmk.py:245 in _process_request
#       resp = page_handler(ctx)
#   lib/python3/cmk/gui/wsgi/applications/utils.py:140 in _call_auth
#       handler(ctx)
#   lib/python3/cmk/gui/main.py:30 in page_index
#       SidebarRenderer().show(
#   lib/python3/cmk/gui/sidebar/__init__.py:440 in show
#       self._show_sidebar(
#   lib/python3/cmk/gui/sidebar/__init__.py:482 in _show_sidebar
#       user_config = UserSidebarConfig(user, sidebar_config, user_permissions)
#   lib/python3/cmk/gui/sidebar/__init__.py:239 in __init__
#       self._config = self._load(user_permissions)
#   lib/python3/cmk/gui/sidebar/__init__.py:303 in _load
#       user_config = self._user_config()
#   lib/python3/cmk/gui/sidebar/__init__.py:296 in _user_config
#       return self._user.get_sidebar_configuration(self._initial_config())
#   lib/python3/cmk/gui/sidebar/__init__.py:287 in _initial_config
#       if snapin_registry[snapin[0]].included_in_default_sidebar()
#
# Not in this crash report:
#   - user 'spommer' recreated with role(s) only - its rights are a guess

versions:
  2.5.0p1:
    edition: pro
sites:
  crash_dcbc2498:
    version: 2.5.0p1
    omd_config:
      CORE: cmc
    users:
      spommer:
        fullname: crash dcbc2498
        password: cmk-up-enrolled
        roles:
        - admin

# The innermost frame's locals:
#   self = '<cmk.gui.sidebar.UserSidebarConfig object at 0x7f51a70f9d10>'
```
