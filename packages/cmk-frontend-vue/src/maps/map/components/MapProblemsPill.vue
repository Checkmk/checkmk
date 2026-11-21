<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How much is wrong across a whole map, at the top of the page.

It earns its place because a map can hide this: a flow map with its services
switched off shows nothing but green dots however many of them are failing.
With nothing wrong, it is not shown at all. Informational only — the map's
own controls are where something is done about it, so this is not a call to
action.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { stateShortWordFromToken } from '@/maps/utils/objectAria'

/** What is wrong across a whole map: its hosts down or unreachable, and its hosts' services. */
export interface ProblemCounts {
  down: number
  unreachable: number
  critical: number
  warning: number
  unknown: number
  hostsWithProblems: number
}

const { _t, _tn } = usei18n()

const props = defineProps<{ problems: ProblemCounts }>()

const serviceProblems = computed(
  () => props.problems.critical + props.problems.warning + props.problems.unknown
)

/** Each count that is not zero, by Checkmk's short state name, the worst first. */
const shortCounts = computed(() => {
  const { down, unreachable, critical, unknown, warning } = props.problems
  const counts: [number, string][] = [
    [down, 'DOWN'],
    [unreachable, 'UNREACHABLE'],
    [critical, 'CRITICAL'],
    [unknown, 'UNKNOWN'],
    [warning, 'WARNING']
  ]
  return counts
    .filter(([count]) => count)
    .map(([count, state]) =>
      _t('%{count} %{state}', { count, state: stateShortWordFromToken(_t, state) })
    )
    .join(' · ')
})

const title = computed(() => {
  const { down, unreachable, hostsWithProblems } = props.problems
  const n = serviceProblems.value
  const hosts = [
    down ? _tn('%{n} host down', '%{n} hosts down', down, { n: down }) : '',
    unreachable
      ? _tn('%{n} host unreachable', '%{n} hosts unreachable', unreachable, { n: unreachable })
      : ''
  ]
    .filter(Boolean)
    .join(', ')
  const services = !n
    ? ''
    : hostsWithProblems === 1
      ? _tn('%{n} service problem on one host', '%{n} service problems on one host', n, { n })
      : _tn(
          '%{n} service problem on %{hosts} hosts',
          '%{n} service problems on %{hosts} hosts',
          n,
          {
            n,
            hosts: hostsWithProblems
          }
        )
  return [hosts, services].filter(Boolean).join('; ')
})
</script>

<template>
  <span
    v-if="serviceProblems + problems.down + problems.unreachable > 0"
    class="maps-map-problems-pill"
    :class="
      problems.down > 0 || problems.critical > 0
        ? 'maps-map-problems-pill--critical'
        : 'maps-map-problems-pill--warning'
    "
    :title="title"
  >
    <CmkIcon name="problem" size="small" />
    {{ shortCounts }}
  </span>
</template>

<style scoped>
.maps-map-problems-pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  border-radius: 9999px;
  transition: all 0.15s;
}

.maps-map-problems-pill--critical {
  color: var(--status-text-color-error-on-tint);
  background: color-mix(in srgb, var(--color-state-critical) var(--status-tint-mix), transparent);
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--color-state-critical) var(--status-tint-border-mix), transparent);
}

.maps-map-problems-pill--warning {
  color: var(--status-text-color-warning-strong);
  background: color-mix(in srgb, var(--color-state-warning) var(--status-tint-mix), transparent);
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--color-state-warning) var(--status-tint-border-mix), transparent);
}
</style>
