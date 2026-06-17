<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { StringArrayPropDef } from '@ucl/_ucl/types/prop-def'

import {
  type DualListElement,
  type SearchableListWidthVariants
} from '@/components/CmkDualList/index.ts'

import codeExample from './UclCmkDualListCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Moves keyboard focus sequentially between the searchable lists and the action buttons.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus in reverse order between the searchable lists and the action buttons.'
  },
  {
    keys: ['Enter', 'Space'],
    description:
      'Triggers the selected action button (e.g., adding or removing items between lists).'
  }
]

export const panelConfig = {
  title: {
    type: 'string' as const,
    title: 'Group Title',
    initialState: 'Assign User Roles'
  },
  width: {
    type: 'list' as const,
    title: 'Width',
    options: [
      { title: 'XSmall', name: 'xsmall' },
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' }
    ] satisfies Options<SearchableListWidthVariants>[],
    initialState: 'medium' as const
  },
  selectedData: {
    type: 'string-array' as const,
    title: 'selectedData',
    initialState: ['host_admin'],
    help: 'Type: string[]. IDs must match the name of each available element. In the UCL app, enter one ID per line in the textarea, e.g.:host_admin network_admin db_admin'
  }
} satisfies PanelConfigFor<typeof CmkDualList, 'modelValue' | 'externalErrors' | 'elements'> & {
  selectedData: StringArrayPropDef
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

import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'

defineProps<{ screenshotMode: boolean }>()

const elements: DualListElement[] = [
  { name: 'host_admin', title: 'Host Administrator' },
  { name: 'network_admin', title: 'Network Administrator' },
  { name: 'db_admin', title: 'Database Administrator' },
  { name: 'security_auditor', title: 'Security Auditor' },
  { name: 'guest', title: 'Guest User' },
  {
    name: 'infra_ops',
    title: 'Infrastructure Operations Admin with read/write access to hosts and services'
  }
]

const propState = new PanelStateCreator<
  typeof CmkDualList,
  'modelValue' | 'externalErrors' | 'elements'
>().createRef(panelConfig)

const selectedData = computed({
  get: (): DualListElement[] =>
    elements.filter((el) => (propState.value.selectedData as string[]).includes(el.name)),
  set: (val: DualListElement[]) => {
    propState.value.selectedData = val.map((el) => el.name)
  }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkDualList</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkDualList
        v-model="selectedData"
        :elements="elements"
        :title="propState.title"
        :width="propState.width"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
