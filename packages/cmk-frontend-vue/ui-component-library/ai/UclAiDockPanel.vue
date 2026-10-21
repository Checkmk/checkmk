<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'

import type { AiDockPanelDock } from '@/ai/components/AiDockPanel.vue'

import codeExample from './UclAiDockPanelCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the resize handle.'
  },
  {
    keys: [['Shift', 'Tab']],
    description:
      'Moves focus to the resize handle from the next focusable element in reverse order.'
  },
  {
    keys: ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'],
    description:
      'Grows the pane away from its edge or shrinks it towards its edge by 50 pixels when the handle is focused.'
  },
  {
    keys: ['Enter'],
    description: 'Collapses the pane.'
  }
]

export const panelConfig = {
  size: {
    type: 'number' as const,
    title: 'size',
    initialState: 200,
    help: 'Two-way (v-model:size). Size of the pane without its border, in pixels.'
  },
  collapsed: {
    type: 'boolean' as const,
    title: 'collapsed',
    initialState: false,
    help: 'Two-way (v-model:collapsed). Hides or shows the pane.'
  },
  dock: {
    type: 'list' as const,
    title: 'dock',
    options: listOptions<AiDockPanelDock>({
      right: 'Right',
      left: 'Left',
      bottom: 'Bottom'
    }),
    initialState: 'right' as const,
    help: 'The edge of the positioned container the pane is attached to.'
  },
  minSize: {
    type: 'number' as const,
    title: 'minSize',
    initialState: 120,
    help: 'Minimum size of the pane, in pixels. Dragging below half of it collapses the pane.'
  }
} satisfies PanelConfigFor<typeof AiDockPanel>
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

import AiDockPanel from '@/ai/components/AiDockPanel.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof AiDockPanel>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>AI dock panel</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        style="
          position: relative;
          width: 100%;
          height: 300px;
          overflow: hidden;
          border: 1px solid var(--default-border-color);
          border-radius: var(--border-radius);
        "
      >
        <div style="padding: var(--dimension-4)">
          <p>Page content.</p>
        </div>
        <AiDockPanel
          v-model:size="propState.size"
          v-model:collapsed="propState.collapsed"
          :dock="propState.dock"
          :min-size="propState.minSize"
        >
          <div
            style="
              box-sizing: border-box;
              height: 100%;
              padding: var(--dimension-4);
              background-color: var(--default-bg-color);
            "
          >
            <p>Docked pane.</p>
          </div>
        </AiDockPanel>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
