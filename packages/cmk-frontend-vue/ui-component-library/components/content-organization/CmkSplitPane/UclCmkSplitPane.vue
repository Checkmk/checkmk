<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { CmkSplitPaneProps } from 'cmk-ui-library/components/CmkSplitPane.vue'

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
    description: 'Moves the handle as far left as the size limits allow.'
  },
  {
    keys: ['End'],
    description: 'Moves the handle as far right as the size limits allow.'
  },
  {
    keys: ['Enter'],
    description: 'Toggles the collapsed state of the docked pane.'
  }
]

export const panelConfig = {
  collapsed: {
    type: 'boolean' as const,
    title: 'collapsed',
    initialState: false,
    help: 'Two-way (v-model:collapsed). Hides or shows the docked pane.'
  },
  dock: {
    type: 'list' as const,
    title: 'dock',
    options: listOptions<NonNullable<CmkSplitPaneProps['dock']>>({
      right: 'Right',
      left: 'Left'
    }),
    initialState: 'right' as const,
    help: 'The pane that can be resized within its limits and collapsed; the other pane fills the rest.'
  },
  paneMinSize: {
    type: 'number' as const,
    title: 'paneMinSize',
    initialState: 20,
    help: 'Minimum size of the docked pane, expressed in sizeUnit.'
  },
  paneMaxSize: {
    type: 'number' as const,
    title: 'paneMaxSize',
    initialState: 50,
    help: 'Maximum size of the docked pane, expressed in sizeUnit.'
  },
  paneDefaultSize: {
    type: 'number' as const,
    title: 'paneDefaultSize',
    initialState: 30,
    help: 'Initial size of the docked pane, expressed in sizeUnit.'
  },
  paneMinWidth: {
    type: 'string' as const,
    title: 'paneMinWidth',
    initialState: '',
    help: 'CSS length the docked pane never renders below, e.g. "520px". Empty means no floor.'
  },
  sizeUnit: {
    type: 'list' as const,
    title: 'sizeUnit',
    options: listOptions<NonNullable<CmkSplitPaneProps['sizeUnit']>>({
      '%': 'Percent (responsive)',
      px: 'Pixels (fixed)'
    }),
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
    help: 'When enabled, dragging the handle below the minimum size collapses the docked pane.'
  },
  hideHandleWhenCollapsed: {
    type: 'boolean' as const,
    title: 'hideHandleWhenCollapsed',
    initialState: true,
    help: 'When enabled, the resize handle is hidden while the docked pane is collapsed.'
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
import CmkSplitPane from 'cmk-ui-library/components/CmkSplitPane.vue'

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
          :dock="propState.dock"
          :pane-min-size="propState.paneMinSize"
          :pane-max-size="propState.paneMaxSize"
          :pane-default-size="propState.paneDefaultSize"
          :pane-min-width="propState.paneMinWidth || undefined"
          :size-unit="propState.sizeUnit"
          :keyboard-resize-by="propState.keyboardResizeBy"
          :collapsible-on-resize="propState.collapsibleOnResize"
          :hide-handle-when-collapsed="propState.hideHandleWhenCollapsed"
        >
          <template #left>
            <div style="padding: var(--dimension-4)">
              <p>Left pane.</p>
            </div>
          </template>
          <template #right>
            <div style="padding: var(--dimension-4)">
              <p>Right pane.</p>
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
