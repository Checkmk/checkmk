<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import {
  type DualListElement,
  type SearchableListWidthVariants
} from '@/components/CmkDualList/index.ts'

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
export const codeExample = `<script setup lang="ts">
import { ref } from 'vue'
${'import'} CmkDualList from '@/components/CmkDualList/CmkDualList.vue'
${'import'} { type DualListElement } from '@/components/CmkDualList/index.ts'

const availableRoles = ref<DualListElement[]>([
  { name: 'admin', title: 'Admin' },
  { name: 'editor', title: 'Editor' },
  { name: 'viewer', title: 'Viewer' }
])


const selectedRoles = ref<DualListElement[]>([availableRoles.value[2]!])
<${'/'}script>

<template>
  <CmkDualList
    v-model:data="selectedRoles"
    :elements="availableRoles"
    title="Assign User Roles"
    :validators="[]"
    :backendValidation="[]"
    width="medium"
  />
</template>`
export const panelConfig = {
  title: {
    type: 'string',
    title: 'Group Title',
    initialState: 'Assign User Roles'
  },
  width: {
    type: 'list',
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
    type: 'string-array',
    title: 'selectedData',
    initialState: ['host_admin'],
    help: 'Type: string[]. IDs must match the name of each available element. In the UCL app, enter one ID per line in the textarea, e.g.:host_admin network_admin db_admin'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { computed, ref } from 'vue'

import CmkDualList from '@/components/CmkDualList/CmkDualList.vue'

defineProps<{ screenshotMode: boolean }>()

const elements: DualListElement[] = [
  { name: 'host_admin', title: 'Host Administrator' },
  { name: 'network_admin', title: 'Network Administrator' },
  { name: 'db_admin', title: 'Database Administrator' },
  { name: 'security_auditor', title: 'Security Auditor' },
  { name: 'guest', title: 'Guest User' }
]

const propState = ref(createPanelState(panelConfig))

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
        v-model:data="selectedData"
        :elements="elements"
        :title="propState.title"
        :validators="[]"
        :backend-validation="[]"
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
