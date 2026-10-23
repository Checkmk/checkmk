<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclCmkTooltipCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves focus to the trigger, which shows the tooltip.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus away from the trigger, which hides the tooltip.'
  },
  {
    keys: ['Escape'],
    description: 'Hides the tooltip while focus stays on the trigger.'
  }
]

type SideOptions = 'top' | 'right' | 'bottom' | 'left'
type AlignOptions = 'start' | 'center' | 'end'
type VariantOptions = 'text' | 'content'
type TitleAlignOptions = 'left' | 'center' | 'right'

const isContentVariant = (state: Record<string, unknown>) => state.variant === 'content'
const isLeftAlignedTitle = (state: Record<string, unknown>) =>
  isContentVariant(state) && state.titleAlign === 'left'

export const panelConfig = {
  open: { type: 'boolean' as const, title: 'Open', initialState: false },
  disableClosingTrigger: {
    type: 'boolean' as const,
    title: 'Disable Closing Trigger',
    initialState: false
  },
  side: {
    type: 'list' as const,
    title: 'Side',
    options: listOptions<SideOptions>({
      top: 'Top',
      right: 'Right',
      bottom: 'Bottom',
      left: 'Left'
    }),
    initialState: 'top' as SideOptions
  },
  align: {
    type: 'list' as const,
    title: 'Align',
    options: listOptions<AlignOptions>({
      start: 'Start',
      center: 'Center',
      end: 'End'
    }),
    initialState: 'center' as AlignOptions
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<VariantOptions>({
      text: 'Text',
      content: 'Content'
    }),
    initialState: 'text' as VariantOptions,
    help: 'Text: a one-line label. Content: a title bar above a content area such as a graph or a legend.'
  },
  title: {
    type: 'string' as const,
    title: 'Title',
    initialState: 'Fr, 2026-03-19',
    hiddenWhen: (state) => !isContentVariant(state)
  },
  titleAside: {
    type: 'string' as const,
    title: 'Title aside',
    initialState: '13:27:59',
    help: 'Always right aligned in regular weight. Only available while the title is left aligned.',
    hiddenWhen: (state) => !isLeftAlignedTitle(state)
  },
  titleBold: {
    type: 'boolean' as const,
    title: 'Bold title',
    initialState: false,
    hiddenWhen: (state) => !isContentVariant(state)
  },
  titleAlign: {
    type: 'list' as const,
    title: 'Title alignment',
    options: listOptions<TitleAlignOptions>({
      left: 'Left',
      center: 'Center',
      right: 'Right'
    }),
    initialState: 'left' as TitleAlignOptions,
    hiddenWhen: (state) => !isContentVariant(state)
  }
} satisfies PanelConfigFor<typeof CmkTooltip> &
  PanelConfigFor<
    typeof CmkTooltipContent,
    'asChild' | 'sideOffset' | 'avoidCollisions' | 'usePortal'
  >
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
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import UclCmkTooltipDev from './UclCmkTooltipDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTooltip>().createRef(panelConfig)

const variantProps = computed(() => {
  const { variant, title, titleAside, titleBold, titleAlign } = propState.value
  if (variant === 'text') {
    return { variant }
  }
  if (titleAlign === 'left') {
    return {
      variant,
      title: untranslated(title),
      titleAside: untranslated(titleAside),
      titleBold,
      titleAlign
    }
  }
  return { variant, title: untranslated(title), titleBold, titleAlign }
})

const segments: StateSegment[] = [
  { label: untranslated('OK'), count: 24, color: 'success' },
  { label: untranslated('WARN'), count: 3, color: 'warning' },
  { label: untranslated('CRIT'), count: 1, color: 'danger' },
  { label: untranslated('UNKNOWN'), count: 0, color: 'unknown' },
  { label: untranslated('PENDING'), count: 2, color: 'default' }
]
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTooltip</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTooltipProvider>
        <CmkTooltip
          v-model:open="propState.open"
          :disable-closing-trigger="propState.disableClosingTrigger"
        >
          <CmkTooltipTrigger as-child>
            <CmkButton variant="secondary" @click="propState.open = !propState.open">
              <CmkIcon name="checkmark" variant="inline" size="small" />
              <span>Interact with me</span>
            </CmkButton>
          </CmkTooltipTrigger>

          <CmkTooltipContent
            :side="propState.side"
            :align="propState.align"
            v-bind="variantProps"
            @pointer-down-outside="propState.open = false"
          >
            <CmkStateCountBar v-if="propState.variant === 'content'" :segments="segments" />
            <template v-else>2026-03-20 - 2026-03-28</template>
          </CmkTooltipContent>
        </CmkTooltip>
      </CmkTooltipProvider>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkTooltipDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
