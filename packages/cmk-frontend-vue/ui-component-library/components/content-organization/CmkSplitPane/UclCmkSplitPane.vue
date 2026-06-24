<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'

import type { CmkSplitPaneProps } from '@/components/CmkSplitPane.vue'

import codeExample from './UclCmkSplitPaneCodeExample.vue?raw'

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
    keys: ['ArrowLeft', 'ArrowRight'],
    description: 'Resizes the panes by the keyboardResizeBy step when the handle is focused.'
  },
  {
    keys: ['Home'],
    description: 'Shrinks the right pane to its minimum size.'
  },
  {
    keys: ['End'],
    description: 'Expands the right pane to its maximum size.'
  },
  {
    keys: ['Enter'],
    description: 'Toggles the collapsed state of the right pane.'
  }
]

export const panelConfig = {
  collapsed: {
    type: 'boolean' as const,
    title: 'collapsed',
    initialState: false,
    help: 'Two-way (v-model:collapsed). Hides or shows the right pane.'
  },
  rightMinSize: {
    type: 'number' as const,
    title: 'rightMinSize',
    initialState: 20,
    help: 'Minimum size of the right pane, expressed in sizeUnit.'
  },
  rightMaxSize: {
    type: 'number' as const,
    title: 'rightMaxSize',
    initialState: 50,
    help: 'Maximum size of the right pane, expressed in sizeUnit.'
  },
  rightDefaultSize: {
    type: 'number' as const,
    title: 'rightDefaultSize',
    initialState: 30,
    help: 'Initial size of the right pane, expressed in sizeUnit.'
  },
  sizeUnit: {
    type: 'list' as const,
    title: 'sizeUnit',
    options: [
      { title: 'Percent (responsive)', name: '%' },
      { title: 'Pixels (fixed)', name: 'px' }
    ] satisfies Options<NonNullable<CmkSplitPaneProps['sizeUnit']>>[],
    initialState: '%' as const,
    help: 'Percent sizes scale with the container; pixel sizes stay fixed.'
  },
  keyboardResizeBy: {
    type: 'number' as const,
    title: 'keyboardResizeBy',
    initialState: 10,
    help: 'Step size used when resizing with the arrow keys.'
  },
  collapsibleOnResize: {
    type: 'boolean' as const,
    title: 'collapsibleOnResize',
    initialState: true,
    help: 'When enabled, dragging the handle below the minimum size collapses the right pane.'
  },
  hideHandleWhenCollapsed: {
    type: 'boolean' as const,
    title: 'hideHandleWhenCollapsed',
    initialState: true,
    help: 'When enabled, the resize handle is hidden while the right pane is collapsed.'
  }
} satisfies PanelConfigFor<typeof CmkSplitPane>
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

import CmkSplitPane from '@/components/CmkSplitPane.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkSplitPane>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkSplitPane</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div
        style="
          width: 100%;
          height: 300px;
          border: 1px solid var(--default-border-color);
          border-radius: var(--border-radius);
        "
      >
        <CmkSplitPane
          v-model:collapsed="propState.collapsed"
          :right-min-size="propState.rightMinSize"
          :right-max-size="propState.rightMaxSize"
          :right-default-size="propState.rightDefaultSize"
          :size-unit="propState.sizeUnit"
          :keyboard-resize-by="propState.keyboardResizeBy"
          :collapsible-on-resize="propState.collapsibleOnResize"
          :hide-handle-when-collapsed="propState.hideHandleWhenCollapsed"
        >
          <template #left>
            <div style="padding: var(--dimension-4)">
              <p>Main content area. Drag the green handle to resize the right pane.</p>
            </div>
          </template>
          <template #right>
            <div style="padding: var(--dimension-4)">
              <p>
                Right pane. It can be collapsed by dragging the handle to the edge or via the
                collapsed control.
              </p>
            </div>
          </template>
        </CmkSplitPane>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
