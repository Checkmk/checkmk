<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkSiteOverviewHostsFigureCodeExample.vue?raw'

export const panelConfig = {
  count: {
    type: 'number' as const,
    title: 'Hosts',
    help: 'The number of hosts. All hosts of one colour draw as one path.',
    initialState: 200
  },
  hexagonSize: {
    type: 'list' as const,
    title: 'Hexagon size',
    options: listOptions<'default' | 'large'>({ default: 'Default', large: 'Large' }),
    initialState: 'default' as const
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked hexagons',
    help: 'Gives the widget one resolved link, so the hexagons render as anchors.',
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
} satisfies PanelConfigFor<
  typeof CmkSiteOverviewHostsFigure,
  'value' | 'filters' | 'interactive'
> & {
  count: NumberPropDef
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

import CmkSiteOverviewHostsFigure from '@/dashboard/components/figures/CmkSiteOverviewHostsFigure.vue'
import type { ResolvedLink, SiteOverviewHost, SiteOverviewHosts } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkSiteOverviewHostsFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const LINK: ResolvedLink = {
  title: 'Host',
  location: { type: 'views', name: 'host' },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

const HOST_STATES: readonly Pick<
  SiteOverviewHost,
  'state' | 'in_downtime' | 'num_warn' | 'num_crit' | 'num_unknown'
>[] = [
  { state: 'UP', in_downtime: false, num_warn: 0, num_crit: 0, num_unknown: 0 },
  { state: 'UP', in_downtime: false, num_warn: 2, num_crit: 0, num_unknown: 0 },
  { state: 'UP', in_downtime: false, num_warn: 0, num_crit: 5, num_unknown: 0 },
  { state: 'UP', in_downtime: false, num_warn: 0, num_crit: 0, num_unknown: 1 },
  { state: 'DOWN', in_downtime: false, num_warn: 0, num_crit: 0, num_unknown: 0 },
  { state: 'UP', in_downtime: true, num_warn: 0, num_crit: 0, num_unknown: 0 }
]

const value = computed<SiteOverviewHosts>(() => ({
  mode: 'hosts',
  links: propState.value.linked ? [LINK] : [],
  hosts: Array.from({ length: Math.max(0, Math.floor(propState.value.count)) }, (_, index) => ({
    ...HOST_STATES[(index * 7) % HOST_STATES.length]!,
    site_id: 'heute',
    host_name: `host-${index}`,
    has_been_checked: true,
    num_services: 10,
    link_properties: { links: propState.value.linked ? [{}] : [] }
  }))
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSiteOverviewHostsFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkSiteOverviewHostsFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :hexagon-size="propState.hexagonSize"
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
