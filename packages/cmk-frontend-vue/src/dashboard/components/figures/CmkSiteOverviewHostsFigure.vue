<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type {
  MonitoringState,
  SiteOverviewContent,
  SiteOverviewHost,
  SiteOverviewHosts,
  VisualContext
} from '@/dashboard/types/widget'

import FigureTooltip, { type FigureTooltipContent } from './lib/FigureTooltip.vue'
import HexagonGridFigure, { type HexagonCell } from './lib/HexagonGridFigure.vue'
import { HEXAGON_MAX_BOX_WIDTH, type HexagonStyle } from './lib/hexagon'

const props = defineProps<{
  value: SiteOverviewHosts
  width: number
  height: number
  hexagonSize: SiteOverviewContent['hexagon_size']
  filters: VisualContext
  interactive: boolean
}>()

const { _t, _tn } = usei18n()

type HostState = SiteOverviewHost['state'] | 'DOWNTIME'
type HostHexagonState = Exclude<HostState, 'UP'> | MonitoringState

function opaque(color: string): HexagonStyle {
  return { color, fillOpacity: 1, strokeOpacity: 0 }
}

const HOST_HEXAGON: Record<HostHexagonState, { style: HexagonStyle; text: string }> = {
  DOWN: { style: opaque('var(--color-dark-red-50)'), text: _t('down') },
  UNREACHABLE: { style: opaque('var(--color-orange-50)'), text: _t('unreachable') },
  DOWNTIME: { style: opaque('var(--color-light-blue-50)'), text: _t('in downtime') },
  CRITICAL: { style: opaque('var(--color-dark-red-50)'), text: _t('critical') },
  UNKNOWN: { style: opaque('var(--color-orange-50)'), text: _t('unknown') },
  WARNING: { style: opaque('var(--color-yellow-50)'), text: _t('warning') },
  OK: { style: opaque('var(--db-cmk-site-overview-hosts-figure-ok)'), text: _t('OK') }
}

const INNER_STYLE = opaque('var(--db-cmk-site-overview-hosts-figure-headline)')

const HOST_STATE_TEXT: Record<HostState, string> = {
  UP: _t('Host is up'),
  DOWN: _t('Host is down'),
  UNREACHABLE: _t('Host is unreachable'),
  DOWNTIME: _t('Host is in downtime')
}

const INNER_RADIUS = 0.7
const BADNESS_STEPS: readonly (readonly [number, number])[] = [
  [0.05, 0.05],
  [0.2, 0.3],
  [0.5, 0.6],
  [1, 1]
]

function hostState(host: SiteOverviewHost): HostState {
  return host.in_downtime ? 'DOWNTIME' : host.state
}

function hasHostProblem(host: SiteOverviewHost): boolean {
  return hostState(host) !== 'UP'
}

function numProblems(host: SiteOverviewHost): number {
  return host.num_warn + host.num_crit + host.num_unknown
}

function worstServiceState(host: SiteOverviewHost): MonitoringState {
  if (host.num_crit > 0) {
    return 'CRITICAL'
  }
  if (host.num_unknown > 0) {
    return 'UNKNOWN'
  }
  return host.num_warn > 0 ? 'WARNING' : 'OK'
}

function outerState(host: SiteOverviewHost): HostHexagonState {
  const state = hostState(host)
  return state === 'UP' ? worstServiceState(host) : state
}

function innerScale(host: SiteOverviewHost): number {
  const share = host.num_services === 0 ? 0 : numProblems(host) / host.num_services
  const badness = BADNESS_STEPS.find(([upper]) => share <= upper)?.[1] ?? 1
  return Math.pow((1 - INNER_RADIUS) * (1 - badness) + INNER_RADIUS, 2)
}

const cells = computed<HexagonCell[]>(() =>
  props.value.hosts.map((host) => ({
    label: host.host_name,
    outer: { style: HOST_HEXAGON[outerState(host)].style, scale: 1 },
    inner: hasHostProblem(host) ? null : { style: INNER_STYLE, scale: innerScale(host) },
    links: props.value.links,
    linkProperties: host.link_properties
  }))
)

const figureLabel = computed(() => {
  const counts = new Map<HostHexagonState, number>()
  for (const host of props.value.hosts) {
    const state = outerState(host)
    counts.set(state, (counts.get(state) ?? 0) + 1)
  }
  const total = props.value.hosts.length
  return [
    _tn('%{n} host', '%{n} hosts', total, { n: total }),
    ...[...counts].map(([state, count]) => `${count} ${HOST_HEXAGON[state].text}`)
  ].join(', ')
})

function tooltip(index: number): FigureTooltipContent {
  const host = props.value.hosts[index]!
  const state = HOST_STATE_TEXT[hostState(host)]
  if (hasHostProblem(host)) {
    return { title: host.host_name, state, rows: [] }
  }
  const problems = numProblems(host)
  const worst = HOST_HEXAGON[worstServiceState(host)].text
  let problemText = _t('problem services')
  if (problems === 1) {
    problemText = _t('service in %{state} state', { state: worst })
  } else if (problems > 1) {
    problemText = _t('problem services (worst state: %{state})', { state: worst })
  }
  return {
    title: host.host_name,
    state,
    rows: [
      {
        key: 'services',
        count: host.num_services,
        text: _tn('service', 'services', host.num_services)
      },
      { key: 'problems', count: problems, text: problemText }
    ]
  }
}
</script>

<template>
  <div class="db-cmk-site-overview-hosts-figure">
    <HexagonGridFigure
      :label="figureLabel"
      :cells="cells"
      :width="width"
      :height="height"
      :max-box-width="HEXAGON_MAX_BOX_WIDTH[hexagonSize]"
      :filters="filters"
      :interactive="interactive"
    >
      <template #tooltip="{ index }">
        <FigureTooltip v-bind="tooltip(index)" />
      </template>
    </HexagonGridFigure>
  </div>
</template>

<style scoped>
.db-cmk-site-overview-hosts-figure {
  --db-cmk-site-overview-hosts-figure-ok: rgb(189 189 189);
  --db-cmk-site-overview-hosts-figure-headline: var(--ux-theme-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
[data-theme='modern-dark'] .db-cmk-site-overview-hosts-figure {
  --db-cmk-site-overview-hosts-figure-ok: rgb(58 69 80);
  --db-cmk-site-overview-hosts-figure-headline: var(--ux-theme-3);
}
</style>
