<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
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

type ButtonContent = 'iconAndLabel' | 'label' | 'iconOnly'
type ButtonState = 'default' | 'disabled' | 'running'

export const panelConfig = {
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<ButtonVariants['variant']>({
      primary: 'Primary',
      secondary: 'Secondary',
      optional: 'Optional',
      success: 'Success',
      warning: 'Warning',
      danger: 'Danger',
      info: 'Info',
      text: 'Text',
      ai: 'AI'
    }),
    initialState: 'primary' as const,
    help: 'AI renders the optional button with a purple shimmer sweeping across it, marking an AI-powered action.'
  },
  content: {
    type: 'list' as const,
    title: 'Content',
    options: [
      {
        title: 'Icon and label',
        name: 'iconAndLabel',
        hiddenWhen: (state) => state.variant === 'text'
      },
      { title: 'Label only', name: 'label' },
      {
        title: 'Icon only',
        name: 'iconOnly',
        hiddenWhen: (state) => state.variant !== 'optional'
      }
    ],
    initialState: 'iconAndLabel' as const,
    help: 'Icon only renders a fixed 20px square button and is only available for the Optional variant. The Text variant always shows the label only.'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<'medium' | 'small'>({
      medium: 'Medium',
      small: 'Small'
    }),
    initialState: 'medium' as const,
    hiddenWhen: (state) => state.content === 'iconOnly'
  },
  state: {
    type: 'list' as const,
    title: 'State',
    options: listOptions<ButtonState>({
      default: 'Default',
      disabled: 'Disabled',
      running: 'Running'
    }),
    initialState: 'default' as const,
    help: 'Running pulses the button while the action it triggers is still running.'
  },
  disabledReason: {
    type: 'string' as const,
    title: 'Disabled reason',
    initialState: '',
    help: 'Renders the disabled button as aria-disabled with the reason as its title, so a hover still explains why the action is unavailable.',
    hiddenWhen: (state) => state.state !== 'disabled'
  },
  icon: {
    type: 'list' as const,
    title: 'Icon',
    options: [
      { title: 'Acknowledge', name: 'ack' },
      { title: 'Downtime', name: 'downtime' },
      { title: 'Reload', name: 'reload' },
      { title: 'Save', name: 'save' }
    ],
    initialState: 'downtime' as const,
    hiddenWhen: (state) => state.content === 'label'
  },
  iconSide: {
    type: 'list' as const,
    title: 'Icon side',
    options: [
      { title: 'Left', name: 'left' },
      { title: 'Right', name: 'right' }
    ],
    initialState: 'left' as const,
    hiddenWhen: (state) => state.content !== 'iconAndLabel'
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
  download: {
    type: 'string' as const,
    title: 'Download filename',
    initialState: '',
    help: 'Only applicable if href is set. Suggests a filename when downloading the linked file.'
  },
  title: {
    type: 'string' as const,
    title: 'Tooltip',
    initialState: ''
  }
} satisfies PanelConfigFor<typeof CmkButton, 'icon' | 'disabled' | 'running'> & {
  content: ListPropDef<ButtonContent>
  state: ListPropDef<ButtonState>
  icon: ListPropDef<SimpleIcons>
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

const propState = new PanelStateCreator<
  typeof CmkButton,
  'icon' | 'disabled' | 'running'
>().createRef(panelConfig)

const icon = computed<ButtonIcon | undefined>(() =>
  propState.value.content === 'label'
    ? undefined
    : { name: propState.value.icon, side: propState.value.iconSide }
)

const size = computed(() =>
  propState.value.content === 'iconOnly' ? 'iconOnly' : propState.value.size
)

const disabledReason = computed(() =>
  propState.value.state === 'disabled' && propState.value.disabledReason
    ? untranslated(propState.value.disabledReason)
    : undefined
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkButton</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkButton
        :variant="propState.variant"
        :size="size"
        :disabled="propState.state === 'disabled'"
        :disabled-reason="disabledReason"
        :href="propState.href || undefined"
        :target="propState.target || undefined"
        :download="propState.download || undefined"
        :title="propState.title"
        :icon="icon"
        :running="propState.state === 'running'"
      >
        <template v-if="propState.content !== 'iconOnly'">Click Me</template>
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
