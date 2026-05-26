<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import { allIconOptions } from '@ucl/_ucl/lib/icon'

import { type SimpleIcons } from '@/components/CmkIcon'

import codeExample from './UclCmkPopupDialogCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to the button or link element (if not disabled). While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the button from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Opens the Popup Dialog when the trigger element is focused.'
  },
  {
    keys: ['Escape'],
    description: 'Closes the dialog.'
  }
]

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Open', initialState: false },
  title: { type: 'string' as const, title: 'Title', initialState: 'System Notification' },
  text: {
    type: 'string' as const,
    title: 'Text Content',
    initialState: 'This is a detailed message explaining the context of the dialog.'
  },
  icon: {
    type: 'list' as const,
    title: 'Icon',
    options: [{ title: 'None', name: 'none' }, ...allIconOptions] satisfies Options<
      SimpleIcons | 'none'
    >[],
    initialState: 'alert-crit' as SimpleIcons | 'none'
  },
  okButtonText: { type: 'string' as const, title: 'OK Button Text', initialState: 'Close' },
  stayOpenOverlayClick: {
    type: 'boolean' as const,
    title: 'Prevent Overlay Close',
    initialState: false
  }
} satisfies PanelConfigFor<typeof CmkPopupDialog>
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

import CmkButton from '@/components/CmkButton'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkPopupDialog>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkPopupDialog</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton @click="propState.open = true"> Open Dialog </CmkButton>

      <CmkPopupDialog
        :open="propState.open"
        :title="propState.title"
        :text="propState.text"
        :icon="propState.icon === 'none' ? undefined : (propState.icon as SimpleIcons)"
        :ok-button-text="propState.okButtonText || undefined"
        :stay-open-overlay-click="propState.stayOpenOverlayClick"
        @close="propState.open = false"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
