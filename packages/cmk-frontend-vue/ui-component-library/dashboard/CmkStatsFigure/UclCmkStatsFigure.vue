<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkStatsFigureCodeExample.vue?raw'

type StatsFamily = 'hosts' | 'services' | 'events'

type Scenario =
  | 'empty'
  | 'fine'
  | 'single'
  | 'mixed'
  | 'dominant'
  | 'outage'
  | 'maintenance'
  | 'large'

export const panelConfig = {
  family: {
    type: 'list' as const,
    title: 'Family',
    help: 'Which statistics widget the value comes from. Each family has its own parts.',
    options: listOptions<StatsFamily>({
      hosts: 'Host statistics',
      services: 'Service statistics',
      events: 'Event statistics'
    }),
    initialState: 'hosts' as const
  },
  scenario: {
    type: 'list' as const,
    title: 'Scenario',
    help: 'A fixed set of counts that shows one case of the rings and the table. The events have no downtime part, so their maintenance scenario has no problems.',
    options: listOptions<Scenario>({
      empty: 'No objects',
      fine: 'All fine',
      single: 'One small problem',
      mixed: 'Some problems',
      dominant: 'One dominant problem',
      outage: 'Full outage',
      maintenance: 'Maintenance',
      large: 'Large numbers'
    }),
    initialState: 'mixed' as const
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked parts',
    help: 'Gives the value one resolved link, so every table row renders as an anchor.',
    initialState: true
  },
  width: {
    type: 'number' as const,
    title: 'Width (px)',
    help: 'The measured width the frame hands to the figure. Drag the corner of the preview to change it.',
    initialState: 400
  },
  height: {
    type: 'number' as const,
    title: 'Height (px)',
    initialState: 200
  }
} satisfies PanelConfigFor<typeof CmkStatsFigure, 'value' | 'filters' | 'interactive'> & {
  family: ListPropDef<StatsFamily>
  scenario: ListPropDef<Scenario>
  linked: BoolPropDef
}
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  UclResizablePreview
} from '@ucl/_ucl/components/detail-page'
import { computed } from 'vue'

import CmkStatsFigure from '@/dashboard/components/figures/CmkStatsFigure.vue'
import type { ResolvedLink, Stats, StatsPart } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkStatsFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

type Category = StatsPart['category']

interface FamilyCounts {
  hosts: [up: number, downtime: number, unreachable: number, down: number]
  services: [
    ok: number,
    downtime: number,
    hostDown: number,
    warning: number,
    unknown: number,
    critical: number
  ]
  events: [ok: number, warning: number, unknown: number, critical: number]
}

const CATEGORIES: Record<StatsFamily, Category[]> = {
  hosts: ['up', 'downtime', 'unreachable', 'down'],
  services: ['ok', 'downtime', 'host_down', 'warning', 'unknown', 'critical'],
  events: ['ok', 'warning', 'unknown', 'critical']
}

const COUNTS: Record<Scenario, FamilyCounts> = {
  empty: { hosts: [0, 0, 0, 0], services: [0, 0, 0, 0, 0, 0], events: [0, 0, 0, 0] },
  fine: { hosts: [52, 0, 0, 0], services: [418, 0, 0, 0, 0, 0], events: [37, 0, 0, 0] },
  single: { hosts: [51, 0, 0, 1], services: [417, 0, 0, 0, 0, 1], events: [36, 0, 0, 1] },
  mixed: {
    hosts: [42, 3, 2, 5],
    services: [355, 12, 9, 21, 4, 17],
    events: [28, 5, 1, 3]
  },
  dominant: {
    hosts: [4, 1, 2, 45],
    services: [31, 6, 4, 12, 3, 362],
    events: [3, 2, 1, 31]
  },
  outage: {
    hosts: [0, 0, 12, 40],
    services: [0, 0, 210, 30, 48, 130],
    events: [0, 8, 4, 25]
  },
  maintenance: {
    hosts: [5, 46, 0, 1],
    services: [38, 352, 18, 6, 1, 3],
    events: [37, 0, 0, 0]
  },
  large: {
    hosts: [1187342, 41208, 9613, 120451],
    services: [9823105, 231044, 142287, 441193, 38720, 291136],
    events: [1871204, 84317, 12109, 45238]
  }
}

const LINK: ResolvedLink = {
  title: 'All objects',
  location: { type: 'views', name: 'searchhost' },
  include_context: true,
  include_time_range: false,
  show_filter_form: true
}

const value = computed<Stats>(() => {
  const counts = COUNTS[propState.value.scenario][propState.value.family]
  const linkProperties = propState.value.linked ? { links: [{}] } : { links: [] }
  return {
    links: propState.value.linked ? [LINK] : [],
    parts: CATEGORIES[propState.value.family].map((category, index) => ({
      category,
      count: counts[index]!,
      link_properties: linkProperties
    })),
    total: {
      count: counts.reduce((sum, count) => sum + count, 0),
      link_properties: linkProperties
    }
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkStatsFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkStatsFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :filters="{}"
          :interactive="propState.linked"
        />
      </UclResizablePreview>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
