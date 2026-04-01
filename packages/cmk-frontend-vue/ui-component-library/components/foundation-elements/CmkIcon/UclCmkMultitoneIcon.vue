<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import {
  type CmkMultitoneIconColor,
  type CmkMultitoneIconNames,
  type IconSizeNames
} from '@/components/CmkIcon/types.ts'

export const codeExample = `<script setup lang="ts">
${'import'} CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
<${'/'}script>

<template>
  <CmkMultitoneIcon
    name="services"
    primary-color="success"
    secondary-color="warning"
    size="large"
    title="Service Status"
  />
</template>`
export const panelConfig = {
  name: {
    type: 'list',
    title: 'Icon Name',
    options: [
      { title: 'Services', name: 'services' },
      { title: 'Monitoring', name: 'monitoring' },
      { title: 'Setup', name: 'setup' },
      { title: 'User', name: 'user' },
      { title: 'Success', name: 'success' },
      { title: 'Error', name: 'error' },
      { title: 'Warning', name: 'warning' },
      { title: 'Aggregation (two-color)', name: 'aggr' }
    ] satisfies Options<CmkMultitoneIconNames>[],
    initialState: 'services' as CmkMultitoneIconNames
  },
  size: {
    type: 'list',
    title: 'Size',
    options: [
      { title: 'XX-Small', name: 'xxsmall' },
      { title: 'X-Small', name: 'xsmall' },
      { title: 'Small', name: 'small' },
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'X-Large', name: 'xlarge' },
      { title: 'XX-Large', name: 'xxlarge' },
      { title: 'XXX-Large', name: 'xxxlarge' }
    ] satisfies Options<IconSizeNames>[],
    initialState: 'xxlarge' as const
  },
  primaryColor: {
    type: 'list',
    title: 'Primary Color',
    options: [
      { name: 'success', title: 'Success (Green)' },
      { name: 'danger', title: 'Danger (Red)' },
      { name: 'warning', title: 'Warning (Yellow)' },
      { name: 'info', title: 'Info (Blue)' },
      { name: 'hosts', title: 'Hosts (Cyan)' },
      { name: 'services', title: 'Services (Orange)' },
      { name: 'specialAgents', title: 'Special Agents (Purple)' },
      { name: 'users', title: 'Users (Pink)' },
      { name: 'customization', title: 'Customization (Brown)' },
      { name: 'others', title: 'Others (Grey)' }
    ] satisfies Options<CmkMultitoneIconColor>[],
    initialState: 'success' as const
  },
  secondaryColor: {
    type: 'list',
    title: 'Secondary Color',
    options: [
      { name: 'success', title: 'Success (Green)' },
      { name: 'danger', title: 'Danger (Red)' },
      { name: 'warning', title: 'Warning (Yellow)' },
      { name: 'info', title: 'Info (Blue)' },
      { name: 'hosts', title: 'Hosts (Cyan)' },
      { name: 'services', title: 'Services (Orange)' },
      { name: 'specialAgents', title: 'Special Agents (Purple)' },
      { name: 'users', title: 'Users (Pink)' },
      { name: 'customization', title: 'Customization (Brown)' },
      { name: 'others', title: 'Others (Grey)' }
    ] satisfies Options<CmkMultitoneIconColor>[],
    initialState: 'warning' as const
  },
  rotate: {
    type: 'number',
    title: 'Rotation',
    initialState: 0,
    help: 'Enter a rotation value in degrees (e.g., 45, 90, 180) to rotate the icon.'
  },
  title: {
    type: 'string',
    title: 'Title Attribute',
    initialState: 'Demo Multitone Icon'
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
import { ref } from 'vue'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = ref(createPanelState(panelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkMultitoneIcon</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkMultitoneIcon
        :name="propState.name"
        :primary-color="propState.primaryColor"
        :secondary-color="propState.secondaryColor"
        :size="propState.size"
        :rotate="propState.rotate"
        :title="propState.title"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
