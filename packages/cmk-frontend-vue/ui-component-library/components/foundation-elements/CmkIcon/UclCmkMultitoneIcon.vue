<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import { allMultitoneIconOptions } from '@ucl/_ucl/lib/icon'
import {
  type CmkMultitoneIconColor,
  type CmkMultitoneIconNames,
  type IconSizeNames
} from 'cmk-ui-library/components/CmkIcon/types.ts'

import codeExample from './UclCmkMultitoneIconCodeExample.vue?raw'

export const panelConfig = {
  name: {
    type: 'list' as const,
    title: 'Icon Name',
    options: allMultitoneIconOptions satisfies Options<CmkMultitoneIconNames>[],
    initialState: 'services' as CmkMultitoneIconNames
  },
  size: {
    type: 'list' as const,
    title: 'Size',
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
    initialState: 'xxlarge' as const
  },
  primaryColor: {
    type: 'list' as const,
    title: 'Primary Color',
    options: listOptions<CmkMultitoneIconColor>({
      success: 'Success (Green)',
      danger: 'Danger (Red)',
      warning: 'Warning (Yellow)',
      info: 'Info (Blue)',
      hosts: 'Hosts (Cyan)',
      services: 'Services (Orange)',
      specialAgents: 'Special Agents (Purple)',
      users: 'Users (Pink)',
      customization: 'Customization (Brown)',
      others: 'Others (Grey)',
      font: 'Font (Text Color)'
    }),
    initialState: 'success' as const
  },
  secondaryColor: {
    type: 'list' as const,
    title: 'Secondary Color',
    options: listOptions<CmkMultitoneIconColor>({
      success: 'Success (Green)',
      danger: 'Danger (Red)',
      warning: 'Warning (Yellow)',
      info: 'Info (Blue)',
      hosts: 'Hosts (Cyan)',
      services: 'Services (Orange)',
      specialAgents: 'Special Agents (Purple)',
      users: 'Users (Pink)',
      customization: 'Customization (Brown)',
      others: 'Others (Grey)',
      font: 'Font (Text Color)'
    }),
    initialState: 'warning' as const
  },
  rotate: {
    type: 'number' as const,
    title: 'Rotation',
    initialState: 0,
    help: 'Enter a rotation value in degrees (e.g., 45, 90, 180) to rotate the icon.'
  },
  title: {
    type: 'string' as const,
    title: 'Title Attribute',
    initialState: 'Demo Multitone Icon'
  }
} satisfies PanelConfigFor<typeof CmkMultitoneIcon>
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
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkMultitoneIcon>().createRef(panelConfig)
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
