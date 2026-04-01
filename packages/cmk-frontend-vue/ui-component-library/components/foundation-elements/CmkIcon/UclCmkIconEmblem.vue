<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import { type IconEmblems, type IconSizeNames, type SimpleIcons } from '@/components/CmkIcon/types'

export const codeExample = `<script setup lang="ts">
${'import'} CmkIcon from '@/components/CmkIcon'
${'import'} CmkIconEmblem from '@/components/CmkIcon/CmkIconEmblem.vue'
<${'/'}script>

<template>
  <CmkIconEmblem emblem="warning"><CmkIcon name="filter" size="medium" /></CmkIconEmblem>
</template>`
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageDeveloperPlayground,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel,
  createPanelState
} from '@ucl/_ucl/components/detail-page'
import { ref } from 'vue'

import CmkIcon from '@/components/CmkIcon'
import CmkIconEmblem from '@/components/CmkIcon/CmkIconEmblem.vue'

import UclCmkIconEmblemDev from './UclCmkIconEmblemDev.vue'

defineProps<{ screenshotMode: boolean }>()

const emblemPanelConfig = {
  emblem: {
    type: 'list',
    title: 'emblem',
    options: [
      { title: 'Add', name: 'add' },
      { title: 'API', name: 'api' },
      { title: 'Disable', name: 'disable' },
      { title: 'Download', name: 'download' },
      { title: 'Downtime', name: 'downtime' },
      { title: 'Edit', name: 'edit' },
      { title: 'Enable', name: 'enable' },
      { title: 'More', name: 'more' },
      { title: 'Pending', name: 'pending' },
      { title: 'Refresh', name: 'refresh' },
      { title: 'Remove', name: 'remove' },
      { title: 'Rulesets', name: 'rulesets' },
      { title: 'Search', name: 'search' },
      { title: 'Settings', name: 'settings' },
      { title: 'Sign', name: 'sign' },
      { title: 'Statistic', name: 'statistic' },
      { title: 'Time', name: 'time' },
      { title: 'Trans', name: 'trans' },
      { title: 'Warning', name: 'warning' }
    ] satisfies Options<'' | IconEmblems>[],
    initialState: 'warning' as '' | IconEmblems,
    help: 'Only the fixed IconEmblems set can be used here — these are separate from SimpleIcons.'
  }
} satisfies PanelConfig

const iconPanelConfig = {
  name: {
    type: 'list',
    title: 'name',
    options: [
      { title: 'Filter', name: 'filter' },
      { title: 'Search', name: 'search' },
      { title: 'Save', name: 'save' },
      { title: 'Info Circle', name: 'info-circle' },
      { title: 'Alert Critical', name: 'alert-crit' }
    ] satisfies Options<SimpleIcons>[],
    initialState: 'filter' as SimpleIcons,
    help: 'Any SimpleIcon name can be used as the base icon, not just the options listed here.'
  },
  size: {
    type: 'list',
    title: 'size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Large', name: 'large' },
      { title: 'X-Large', name: 'xlarge' },
      { title: 'XX-Large', name: 'xxlarge' },
      { title: 'XXX-Large', name: 'xxxlarge' }
    ] satisfies Options<IconSizeNames>[],
    initialState: 'xxlarge' as IconSizeNames
  }
} satisfies PanelConfig

const emblemPropState = ref(createPanelState(emblemPanelConfig))
const iconPropState = ref(createPanelState(iconPanelConfig))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIconEmblem</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIconEmblem :emblem="emblemPropState.emblem || undefined">
        <CmkIcon :name="iconPropState.name" :size="iconPropState.size" />
      </CmkIconEmblem>

      <template #properties>
        <UclPropertiesPanel
          v-model="emblemPropState"
          title="CmkIconEmblem"
          :config="emblemPanelConfig"
        />
        <UclPropertiesPanel v-model="iconPropState" title="CmkIcon" :config="iconPanelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkIconEmblemDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
