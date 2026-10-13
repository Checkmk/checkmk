<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import {
  type StateTagKind,
  type StateTagSize,
  type StateTone
} from 'cmk-ui-library/components/StateTag.vue'

import codeExample from './UclStateTagCodeExample.vue?raw'

export const panelConfig = {
  label: {
    type: 'string' as const,
    title: 'Label',
    initialState: 'OK'
  },
  tone: {
    type: 'list' as const,
    title: 'Tone',
    options: listOptions<StateTone>({
      ok: 'OK',
      warning: 'Warning',
      critical: 'Critical',
      unknown: 'Unknown',
      pending: 'Pending'
    }),
    initialState: 'ok' as const
  },
  kind: {
    type: 'list' as const,
    title: 'Kind',
    options: listOptions<StateTagKind>({
      host: 'Host',
      service: 'Service'
    }),
    initialState: 'host' as const
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<StateTagSize>({
      default: 'Default',
      compact: 'Compact',
      inline: 'Inline'
    }),
    initialState: 'default' as const
  },
  stale: {
    type: 'boolean' as const,
    title: 'Stale',
    initialState: false
  }
} satisfies PanelConfigFor<typeof StateTag>
</script>

<script setup lang="ts">
import {
  PanelStateCreator,
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import StateTag from 'cmk-ui-library/components/StateTag.vue'

import UclStateTagDev from './UclStateTagDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof StateTag>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>StateTag</UclDetailPageHeader>

    <UclDetailPageComponent>
      <StateTag
        :label="propState.label"
        :tone="propState.tone"
        :kind="propState.kind"
        :size="propState.size"
        :stale="propState.stale"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclStateTagDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
