<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef, ListPropDef } from '@ucl/_ucl/types/prop-def'

import type { ObjectState } from '@/dashboard/types/widget'

import codeExample from './UclCmkStateFigureCodeExample.vue?raw'

type State = ObjectState['state']

export const panelConfig = {
  state: {
    type: 'list' as const,
    title: 'State',
    help: 'The state of the host or the service, as the server reports it.',
    options: listOptions<State>({
      UP: 'Host up',
      DOWN: 'Host down',
      UNREACHABLE: 'Host unreachable',
      OK: 'Service OK',
      WARNING: 'Service warning',
      CRITICAL: 'Service critical',
      UNKNOWN: 'Service unknown'
    }),
    initialState: 'CRITICAL' as const
  },
  checked: {
    type: 'boolean' as const,
    title: 'Has been checked',
    help: 'An object that has never been checked shows as pending.',
    initialState: true
  },
  tintBackground: {
    type: 'boolean' as const,
    title: 'Tinted background',
    help: 'The server decides this from the status display and the state.',
    initialState: true
  },
  showPluginOutput: {
    type: 'boolean' as const,
    title: 'Plugin output',
    help: 'The server sends the plugin output only for a problem and only if the widget shows a summary.',
    initialState: true
  },
  linked: {
    type: 'boolean' as const,
    title: 'Linked state',
    help: 'Gives the state one resolved link, so the state renders as an anchor.',
    initialState: true
  },
  width: {
    type: 'number' as const,
    title: 'Width (px)',
    help: 'The measured width the frame hands to the figure.',
    initialState: 300
  },
  height: {
    type: 'number' as const,
    title: 'Height (px)',
    initialState: 200
  }
} satisfies PanelConfigFor<typeof CmkStateFigure, 'value' | 'filters' | 'interactive'> & {
  state: ListPropDef<State>
  checked: BoolPropDef
  tintBackground: BoolPropDef
  showPluginOutput: BoolPropDef
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
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import { computed } from 'vue'

import CmkStateFigure from '@/dashboard/components/figures/CmkStateFigure.vue'
import type { ResolvedLink } from '@/dashboard/types/widget'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<
  typeof CmkStateFigure,
  'value' | 'filters' | 'interactive'
>().createRef(panelConfig)

const LINK: ResolvedLink = {
  title: 'Service',
  location: { type: 'views', name: 'service' },
  include_context: false,
  include_time_range: false,
  show_filter_form: false
}

const value = computed<ObjectState>(() => ({
  links: propState.value.linked ? [LINK] : [],
  link_properties: { links: propState.value.linked ? [{}] : [] },
  state: propState.value.state,
  has_been_checked: propState.value.checked,
  tint_background: propState.value.tintBackground,
  plugin_output: propState.value.showPluginOutput ? 'CPU load is 4.2 (warn/crit at 2.0/4.0)' : null
}))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkStateFigure</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-cmk-state-figure__container">
        <CmkStateFigure
          :value="value"
          :width="Math.max(0, propState.width)"
          :height="Math.max(0, propState.height)"
          :filters="{}"
          :interactive="propState.linked"
        />
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-cmk-state-figure__container {
  display: inline-block;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
