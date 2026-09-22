<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How much is wrong across a whole map, at the top of the page.

It earns its place because a map can hide this: a flow map with its services
switched off shows nothing but green dots however many of them are failing.
Informational only — the map's own controls are where something is done about
it, so this is not a call to action.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'

/**
 * What is wrong across a whole map, counted over its hosts' services.
 *
 * A type rather than an interface, because the counts are handed straight to a
 * translation's interpolation, and only a type alias carries the implicit index
 * signature that asks for.
 */
export type ProblemCounts = {
  critical: number
  warning: number
  hostsWithProblems: number
  /** Unknown included, so an unknown-only map still says something. */
  total: number
}

const { _t } = usei18n()

const props = defineProps<{ problems: ProblemCounts }>()
</script>

<template>
  <span
    class="maps-map-problems-pill"
    :class="
      problems.critical > 0 ? 'maps-map-problems-pill--critical' : 'maps-map-problems-pill--warning'
    "
    :title="
      _t(
        '%{total} service issues (%{critical} critical, %{warning} warning) across %{hostsWithProblems} hosts',
        props.problems
      )
    "
  >
    <CmkIcon name="problem" size="small" />
    {{ _t('%{critical} crit · %{warning} warn', props.problems) }}
  </span>
</template>

<style scoped>
.maps-map-problems-pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 7px;
  font-size: var(--font-size-normal);
  font-weight: 500;
  line-height: 16px;
  border-radius: 9999px;
  transition: all 0.15s;
}

.maps-map-problems-pill--critical {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent);
}

.maps-map-problems-pill--warning {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}
</style>
