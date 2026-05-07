<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { BoolPropDef } from '@ucl/_ucl/types/prop-def'

import codeExample from './UclCmkListCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus to end of list. While the focus outline is hidden from view, its underlying functionality remains intact.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order through the list elements.'
  },
  {
    keys: ['Enter', 'Space'],
    description: 'Deletes the focused item from the list.'
  }
]

type ListOrientation = 'vertical' | 'horizontal'

export const panelConfig = {
  orientation: {
    type: 'list' as const,
    title: 'Orientation',
    options: [
      { title: 'Vertical', name: 'vertical' },
      { title: 'Horizontal', name: 'horizontal' }
    ] satisfies Options<ListOrientation>[],
    initialState: 'vertical' as const
  },
  showAdd: {
    type: 'boolean' as const,
    title: 'Show Add Button',
    initialState: true
  },
  enableDrag: {
    type: 'boolean' as const,
    title: 'Enable Drag & Drop',
    initialState: false
  }
} satisfies PanelConfigFor<typeof CmkList, 'tryDelete' | 'add' | 'dragCallback'> & {
  showAdd: BoolPropDef
  enableDrag: BoolPropDef
}
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
import { ref } from 'vue'

import CmkList from '@/components/CmkList/CmkList.vue'

import UclCmkListDev from './UclCmkListDev.vue'

defineProps<{ screenshotMode: boolean }>()

const listData = ref({
  titles: ['Primary Server', 'Backup Database', 'Cache Node']
})

const tryDelete = (_index: number) => {
  return true
}

const tryAdd = () => {
  listData.value.titles.push(`New Node ${listData.value.titles.length + 1}`)
  return true
}

const propState = new PanelStateCreator<
  typeof CmkList,
  'tryDelete' | 'add' | 'dragCallback'
>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkList</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkList
        :items-props="listData"
        :orientation="propState.orientation"
        :try-delete="tryDelete"
        :add="{ show: propState.showAdd, tryAdd, label: 'Add Item' }"
        :drag-callbacks="propState.enableDrag ? { onReorder: () => {} } : null"
      >
        <template #item-props="{ index, titles }">
          {{ titles }} <small style="opacity: 0.6">(ID: {{ index }})</small>
        </template>
      </CmkList>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkListDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
