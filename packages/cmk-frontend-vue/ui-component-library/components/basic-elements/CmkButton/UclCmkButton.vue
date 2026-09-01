<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfigFor } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'
import type { ButtonVariants } from 'cmk-ui-library/components/CmkButton'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon'

import codeExample from './UclCmkButtonCodeExample.vue?raw'

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
    description:
      'Activates the button. If rendered as a link (via the href prop), Enter follows the link.'
  }
]

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: [
      { title: 'Optional', name: 'optional' },
      { title: 'Primary', name: 'primary' },
      { title: 'Secondary', name: 'secondary' },
      { title: 'Success', name: 'success' },
      { title: 'Warning', name: 'warning' },
      { title: 'Danger', name: 'danger' },
      { title: 'Info', name: 'info' },
      { title: 'Text', name: 'text' },
      { title: 'AI', name: 'ai' }
    ] satisfies Options<ButtonVariants['variant']>[],
    initialState: 'optional' as const,
    help: 'AI renders the optional button with a purple shimmer sweeping across it, marking an AI-powered action.'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: [
      { title: 'Medium', name: 'medium' },
      { title: 'Small', name: 'small' },
      { title: 'Icon only', name: 'iconOnly' }
    ] satisfies Options<ButtonVariants['size']>[],
    initialState: 'medium' as const,
    help: 'Icon only renders a fixed 20px square button with no padding, for an icon-only button.'
  },
  disabled: {
    type: 'boolean' as const,
    title: 'Disabled',
    initialState: false
  },
  disabledReason: {
    type: 'string' as const,
    title: 'Disabled reason',
    initialState: '',
    help: 'Renders the disabled button as aria-disabled with the reason as its title, so a hover still explains why the action is unavailable.'
  },
  icon: {
    type: 'list' as const,
    title: 'Icon',
    options: [
      { title: 'None', name: '' },
      { title: 'Acknowledge', name: 'ack' },
      { title: 'Downtime', name: 'downtime' },
      { title: 'Reload', name: 'reload' },
      { title: 'Save', name: 'save' }
    ],
    initialState: '' as const,
    help: 'Renders the icon left of the content, with the label spacing handled by the button.'
  },
  iconSide: {
    type: 'list' as const,
    title: 'Icon side',
    options: [
      { title: 'Left', name: 'left' },
      { title: 'Right', name: 'right' }
    ],
    initialState: 'left' as const
  },
  href: {
    type: 'string' as const,
    title: 'Href',
    initialState: '',
    help: 'Href attribute renders as a link.'
  },
  target: {
    type: 'list' as const,
    title: 'Target',
    options: [
      { title: 'None', name: '' },
      { title: '_blank', name: '_blank' },
      { title: '_self', name: '_self' }
    ],
    initialState: '',
    help: 'Only applicable if href is set. Specifies where to open the linked document.'
  },
  title: {
    type: 'string' as const,
    title: 'Title Attribute',
    initialState: ''
  },
  running: {
    type: 'boolean' as const,
    title: 'Running',
    initialState: false,
    help: 'Pulses the button while the action it triggers is still running.'
  }
} satisfies PanelConfigFor<typeof CmkButton, 'icon'> & {
  icon: ListPropDef<SimpleIcons | ''>
  iconSide: ListPropDef<'left' | 'right'>
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
import type { ButtonIcon } from 'cmk-ui-library/components/CmkButton'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import UclCmkButtonDev from './UclCmkButtonDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkButton, 'icon'>().createRef(panelConfig)

const icon = computed<ButtonIcon | undefined>(() =>
  propState.value.icon === ''
    ? undefined
    : { name: propState.value.icon, side: propState.value.iconSide }
)

const disabledReason = computed(() =>
  propState.value.disabledReason ? untranslated(propState.value.disabledReason) : undefined
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton
        :variant="propState.variant"
        :size="propState.size"
        :disabled="propState.disabled"
        :disabled-reason="disabledReason"
        :href="propState.href || undefined"
        :target="propState.target || undefined"
        :title="propState.title"
        :icon="icon"
        :running="propState.running"
      >
        Click Me
      </CmkButton>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkButtonDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
