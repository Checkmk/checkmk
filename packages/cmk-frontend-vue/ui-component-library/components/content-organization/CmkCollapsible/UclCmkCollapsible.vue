<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'

import codeExample from './UclCmkCollapsibleCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to title. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the title from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'When the title button is focused, pressing Enter or Space opens the collapsible content.'
  }
]

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Open', initialState: false },
  title: { type: 'string' as const, title: 'Title Text', initialState: 'Collapsible Section' },
  icon: {
    type: 'list' as const,
    title: 'Icon',
    options: [
      { title: 'None', name: 'none' },
      { title: 'Alert Critical', name: 'alert-crit' },
      { title: 'Checkmark', name: 'check' }
    ],
    initialState: 'none'
  },
  disabled: { type: 'boolean' as const, title: 'Disabled', initialState: false },
  sideTitle: { type: 'string' as const, title: 'Side Title', initialState: 'Details' },
  helpText: { type: 'string' as const, title: 'Help Text', initialState: 'Click to expand' }
} satisfies PanelConfigFor<typeof CmkCollapsible, 'contentId'> &
  PanelConfigFor<typeof CmkCollapsibleTitle, 'focus'>
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

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIndent from '@/components/CmkIndent.vue'

import UclCmkCollapsibleDev from './UclCmkCollapsibleDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkCollapsible, 'contentId'>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkCollapsible</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkCollapsibleTitle
        :title="propState.title"
        :side-title="propState.sideTitle"
        :help-text="propState.helpText"
        :open="propState.open"
        :icon="
          propState.icon === 'none'
            ? null
            : ({ type: 'default_icon', id: propState.icon } as DynamicIcon)
        "
        :disabled="propState.disabled"
        @toggle-open="propState.open = !propState.open"
      />

      <CmkCollapsible :open="propState.open">
        <CmkIndent>
          This content is hidden inside the collapsible wrapper. It animates height smoothly when
          toggled.
        </CmkIndent>
      </CmkCollapsible>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkCollapsibleDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
