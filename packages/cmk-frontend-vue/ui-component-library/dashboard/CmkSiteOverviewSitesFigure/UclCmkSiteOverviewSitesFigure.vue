<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, NumberPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkSiteOverviewSitesFigureCodeExample.vue?raw'

export const panelConfig = {
  count: {
    type: 'number' as const,
    title: 'Sites',
    help: 'The number of sites. Every fifth site is offline, with the next offline status in turn.',
    initialState: 6
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
  typeof CmkSiteOverviewSitesFigure,
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

import CmkSiteOverviewSitesFigure from '@/dashboard/components/figures/CmkSiteOverviewSitesFigure.vue'
import type { ResolvedLink, SiteOverviewSites } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkSiteOverviewSitesFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const LINK: ResolvedLink = {
  title: 'Site',
  location: { type: 'dashboards', name: 'site', owner: null },
  include_context: true,
  include_time_range: false,
  show_filter_form: false
}

type OfflineStatus = Exclude<SiteOverviewSites['sites'][number]['status'], 'online'>

const OFFLINE_STATUSES: readonly OfflineStatus[] = [
  'down',
  'unreach',
  'dead',
  'disabled',
  'waiting',
  'missing',
  'unknown'
]

const value = computed<SiteOverviewSites>(() => {
  const linkProperties = { links: propState.value.linked ? [{}] : [] }
  return {
    mode: 'sites',
    links: propState.value.linked ? [LINK] : [],
    sites: Array.from({ length: Math.max(0, Math.floor(propState.value.count)) }, (_, index) =>
      index % 5 === 4
        ? {
            status: OFFLINE_STATUSES[Math.floor(index / 5) % OFFLINE_STATUSES.length]!,
            site_id: `site-${index}`,
            alias: `Site ${index}`
          }
        : {
            status: 'online' as const,
            site_id: `site-${index}`,
            alias: `Site ${index}`,
            parts: [
              { category: 'critical' as const, count: index % 3 },
              { category: 'unknown' as const, count: 1 },
              { category: 'warning' as const, count: index % 4 },
              { category: 'downtime' as const, count: 2 },
              { category: 'ok' as const, count: 10 * (index + 1) }
            ],
            link_properties: linkProperties
          }
    )
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSiteOverviewSitesFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <UclResizablePreview v-model:width="propState.width" v-model:height="propState.height">
        <CmkSiteOverviewSitesFigure
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
