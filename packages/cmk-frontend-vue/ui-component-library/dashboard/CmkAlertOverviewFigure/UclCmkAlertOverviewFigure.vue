<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkAlertOverviewFigureCodeExample.vue?raw'

export const panelConfig = {
  count: {
    type: 'number' as const,
    title: 'Objects',
    help: 'The number of hosts and services with alerts. All objects of one colour step draw as one path.',
    initialState: 150
  },
  maxProblems: {
    type: 'number' as const,
    title: 'Most problems',
    help: 'The upper limit of the random problem counts. The colour scale reaches its darkest step at 100 problems at the earliest.',
    initialState: 250
  },
  seed: {
    type: 'number' as const,
    title: 'Random seed',
    help: 'Another seed draws other random counts. The same seed always draws the same counts.',
    initialState: 1
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked hexagons',
    help: 'Gives every object its resolved link, so a hovered object renders as an anchor.',
    initialState: true
  },
  width: {
    type: 'number' as const,
    title: 'Width (px)',
    help: 'The measured width the frame hands to the figure. Drag the corner of the preview to change it.',
    initialState: 600
  },
  height: {
    type: 'number' as const,
    title: 'Height (px)',
    initialState: 300
  }
} satisfies PanelConfigFor<typeof CmkAlertOverviewFigure, 'value' | 'filters' | 'interactive'> & {
  count: NumberPropDef
  maxProblems: NumberPropDef
  seed: NumberPropDef
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

import CmkAlertOverviewFigure from '@/dashboard/components/figures/CmkAlertOverviewFigure.vue'
import type { AlertOverview, ResolvedLink } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkAlertOverviewFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

function link(name: string): ResolvedLink {
  return {
    title: 'Events',
    location: { type: 'views', name },
    include_context: true,
    include_time_range: false,
    show_filter_form: false
  }
}

function randomSource(seed: number): () => number {
  let state = Math.floor(seed) >>> 0
  return () => {
    state = (state + 0x6d2b79f5) >>> 0
    let mixed = Math.imul(state ^ (state >>> 15), state | 1)
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), mixed | 61)
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296
  }
}

const value = computed<AlertOverview>(() => {
  const random = randomSource(propState.value.seed)
  const maxProblems = Math.max(0, Math.floor(propState.value.maxProblems))
  const elements = Array.from(
    { length: Math.max(0, Math.floor(propState.value.count)) },
    (_, index) => {
      const isHost = random() < 0.25
      const problems = Math.round(maxProblems * Math.pow(random(), 3))
      const crit = Math.round(problems * random())
      const warn = Math.round((problems - crit) * random())
      return {
        site_id: 'heute',
        host_name: `host-${Math.floor(random() * 40)}`,
        service_description: isHost ? null : `Service ${index}`,
        num_ok: Math.round(problems * random()),
        num_warn: warn,
        num_crit: crit,
        num_unknown: problems - crit - warn,
        num_problems: problems,
        links: propState.value.linked ? [link(isHost ? 'hostsvcevents' : 'svcevents')] : [],
        link_properties: { links: propState.value.linked ? [{}] : [] }
      }
    }
  )
  return { elements: elements.sort((a, b) => b.num_problems - a.num_problems) }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkAlertOverviewFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkAlertOverviewFigure
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
