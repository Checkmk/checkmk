<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import {
  type CmkIconVariants,
  type IconEmblems,
  type IconSizeNames,
  type SimpleIcons
} from 'cmk-ui-library/components/CmkIcon/types'

import codeExample from './UclCmkIconEmblemCodeExample.vue?raw'

export const emblemPanelConfig = {
  emblem: {
    type: 'list' as const,
    title: 'emblem',
    options: listOptions<'' | IconEmblems>({
      '': 'None',
      add: 'Add',
      api: 'API',
      disable: 'Disable',
      download: 'Download',
      downtime: 'Downtime',
      edit: 'Edit',
      enable: 'Enable',
      more: 'More',
      pending: 'Pending',
      refresh: 'Refresh',
      remove: 'Remove',
      rulesets: 'Rulesets',
      search: 'Search',
      settings: 'Settings',
      sign: 'Sign',
      statistic: 'Statistic',
      time: 'Time',
      trans: 'Trans',
      warning: 'Warning'
    }),
    initialState: 'warning' as '' | IconEmblems,
    help: 'Only the fixed IconEmblems set can be used here — these are separate from SimpleIcons.'
  },
  colored: { type: 'boolean' as const, title: 'Colored', initialState: true },
  ariaLabel: {
    type: 'string' as const,
    title: 'Aria label',
    initialState: '',
    help: 'Omit when the emblem carries no meaning beyond decoration.'
  }
} satisfies PanelConfigFor<typeof CmkIconEmblem>

export const iconPanelConfig = {
  name: {
    type: 'list' as const,
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
    type: 'list' as const,
    title: 'size',
    options: listOptions<IconSizeNames>({
      xxsmall: 'XX-Small',
      xsmall: 'X-Small',
      small: 'Small',
      medium: 'Medium',
      large: 'Large',
      xlarge: 'X-Large',
      xxlarge: 'XX-Large',
      xxxlarge: 'XXX-Large'
    }),
    initialState: 'xxlarge' as IconSizeNames
  },
  title: { type: 'string' as const, title: 'Title (Tooltip)', initialState: '' },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Plain', name: 'plain' },
      { title: 'Inline', name: 'inline' }
    ],
    initialState: 'plain'
  },
  colored: { type: 'boolean' as const, title: 'Colored', initialState: true },
  rotate: { type: 'number' as const, title: 'Rotation (Degrees)', initialState: 0 }
} satisfies PanelConfigFor<typeof CmkIcon>
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
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkIconEmblem from 'cmk-ui-library/components/CmkIcon/CmkIconEmblem.vue'

import UclCmkIconEmblemDev from './UclCmkIconEmblemDev.vue'

defineProps<{ screenshotMode: boolean }>()

const emblemPropState = new PanelStateCreator<typeof CmkIconEmblem>().createRef(emblemPanelConfig)
const iconPropState = new PanelStateCreator<typeof CmkIcon>().createRef(iconPanelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIconEmblem</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIconEmblem
        :emblem="emblemPropState.emblem || undefined"
        :colored="emblemPropState.colored"
        :aria-label="emblemPropState.ariaLabel || undefined"
      >
        <CmkIcon
          :name="iconPropState.name"
          :size="iconPropState.size"
          :title="iconPropState.title || undefined"
          :variant="iconPropState.variant as CmkIconVariants['variant']"
          :colored="iconPropState.colored"
          :rotate="iconPropState.rotate"
        />
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
