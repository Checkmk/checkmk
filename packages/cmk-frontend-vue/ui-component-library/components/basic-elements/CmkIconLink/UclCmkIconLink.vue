<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import { allIconOptions, allMultitoneIconOptions } from '@ucl/_ucl/lib/icon'

import codeExample from './UclCmkIconLinkCodeExample.vue?raw'

const NO_MULTITONE_COLOR = 'none'

type TargetOption = '_blank' | 'main' | ''

const multitoneColorOptions = [
  { title: 'None (raster icon)', name: NO_MULTITONE_COLOR },
  { name: 'success', title: 'Success (Green)' },
  { name: 'danger', title: 'Danger (Red)' },
  { name: 'warning', title: 'Warning (Yellow)' },
  { name: 'info', title: 'Info (Blue)' },
  { name: 'hosts', title: 'Hosts (Cyan)' },
  { name: 'services', title: 'Services (Orange)' },
  { name: 'specialAgents', title: 'Special Agents (Purple)' },
  { name: 'users', title: 'Users (Pink)' },
  { name: 'customization', title: 'Customization (Brown)' },
  { name: 'others', title: 'Others (Grey)' },
  { name: 'font', title: 'Font colour' }
]

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the link.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus to the link from the next focusable element in reverse order.'
  },
  {
    keys: ['Enter'],
    description: 'Activates the link, following the URL.'
  }
]

export const panelConfig = {
  name: {
    type: 'list' as const,
    title: 'Icon Name',
    help: 'The multitone icons are listed first; they only render as such while a primary color is set.',
    initialState: 'main-help',
    options: [...allMultitoneIconOptions, ...allIconOptions]
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    help: "'inline' vertically centers the icon to surrounding text and adds a right margin; 'plain' leaves it on the text baseline with no spacing.",
    options: [
      { title: 'Plain', name: 'plain' },
      { title: 'Inline (with margin)', name: 'inline' }
    ],
    initialState: 'plain'
  },
  size: {
    type: 'list' as const,
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
    ],
    initialState: 'medium'
  },
  title: {
    type: 'string' as const,
    title: 'Title (Tooltip)',
    initialState: 'Lorem ipsum dolor sit amet'
  },
  rotate: { type: 'number' as const, title: 'Rotation (Degrees)', initialState: 0 },
  colored: { type: 'boolean' as const, title: 'Colored', initialState: true },
  primaryColor: {
    type: 'list' as const,
    title: 'Primary Color',
    help: 'Setting a primary color renders a multitone icon instead of the themed raster icon.',
    options: multitoneColorOptions,
    initialState: NO_MULTITONE_COLOR
  },
  secondaryColor: {
    type: 'list' as const,
    title: 'Secondary Color',
    help: 'Only two-color multitone icons such as "aggr" and "experiment" use it.',
    options: multitoneColorOptions,
    initialState: NO_MULTITONE_COLOR
  },
  href: {
    type: 'string' as const,
    title: 'href',
    initialState: 'https://docs.checkmk.com'
  },
  target: {
    type: 'list' as const,
    title: 'target',
    options: [
      { title: 'None (default)', name: '' },
      { title: '_blank (new tab)', name: '_blank' },
      { title: 'main iframe', name: 'main' }
    ] satisfies Options<TargetOption>[],
    initialState: '' as TargetOption
  }
} satisfies PanelConfigFor<typeof CmkIconLink>
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
import type { CmkIconVariants, IconSizeNames, SimpleIcons } from 'cmk-ui-library/components/CmkIcon'
import type {
  CmkMultitoneIconColor,
  CmkMultitoneIconNames
} from 'cmk-ui-library/components/CmkIcon/types'
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import { computed } from 'vue'

import UclCmkIconLinkDev from './UclCmkIconLinkDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkIconLink>().createRef(panelConfig)

function toMultitoneColor(color: string): NonNullable<CmkMultitoneIconColor> | undefined {
  return color === NO_MULTITONE_COLOR ? undefined : (color as NonNullable<CmkMultitoneIconColor>)
}

const primaryColor = computed(() => toMultitoneColor(propState.value.primaryColor))
const secondaryColor = computed(() => toMultitoneColor(propState.value.secondaryColor))
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkIconLink</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkIconLink
        v-if="primaryColor !== undefined"
        :name="propState.name as CmkMultitoneIconNames"
        :size="propState.size as IconSizeNames"
        :title="propState.title"
        :rotate="propState.rotate"
        :primary-color="primaryColor"
        :secondary-color="secondaryColor"
        :href="propState.href"
        :target="propState.target || undefined"
      />
      <CmkIconLink
        v-else
        :name="propState.name as SimpleIcons"
        :variant="propState.variant as CmkIconVariants['variant']"
        :size="propState.size as IconSizeNames"
        :title="propState.title"
        :rotate="propState.rotate"
        :colored="propState.colored"
        :href="propState.href"
        :target="propState.target || undefined"
      />
      <CmkParagraph>Adjacent text to CmkIconLink </CmkParagraph>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkIconLinkDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
