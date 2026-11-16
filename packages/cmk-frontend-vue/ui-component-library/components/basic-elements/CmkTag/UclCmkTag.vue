<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { ListPropDef } from '@ucl/_ucl/types/prop-def'
import {
  type CmkTagAction,
  type Colors,
  type Sizes,
  type Spacings,
  type Variants
} from 'cmk-ui-library/components/CmkTag.vue'

import codeExample from './UclCmkTagCodeExample.vue?raw'

type ActionPreset = 'none' | 'button' | 'internalLink' | 'externalLink'

const actionPresets: Record<ActionPreset, CmkTagAction | undefined> = {
  none: undefined,
  button: { type: 'button' },
  internalLink: { type: 'link', href: 'view.py?view_name=allhosts', target: '_top' },
  externalLink: { type: 'link', href: 'https://checkmk.com', target: '_blank' }
}

export const panelConfig = {
  content: {
    type: 'string' as const,
    title: 'Content',
    initialState: 'Status Tag'
  },
  value: {
    type: 'string' as const,
    title: 'Value',
    initialState: '',
    help: 'Set in bold after the content, as the value of a key: value label.'
  },
  size: {
    type: 'list' as const,
    title: 'Size',
    options: listOptions<Sizes>({
      small: 'Small',
      medium: 'Medium',
      large: 'Large'
    }),
    initialState: 'medium' as const
  },
  color: {
    type: 'list' as const,
    title: 'Color',
    options: listOptions<Colors>({
      default: 'Default',
      success: 'Success',
      warning: 'Warning',
      unknown: 'Unknown',
      danger: 'Danger',
      discovered: 'Discovered',
      explicit: 'Explicit',
      ruleset: 'Ruleset',
      label: 'Label'
    }),
    initialState: 'default' as const
  },
  variant: {
    type: 'list' as const,
    title: 'Variant',
    options: listOptions<Variants>({
      outline: 'Outline',
      fill: 'Fill',
      weighted: 'Weighted'
    }),
    initialState: 'outline' as const
  },
  spacing: {
    type: 'list' as const,
    title: 'Spacing',
    options: listOptions<Spacings>({
      inline: 'Inline',
      none: 'None'
    }),
    initialState: 'inline' as const,
    help: 'None for a container that spaces its tags itself, e.g. with a flex gap.'
  },
  title: {
    type: 'string' as const,
    title: 'Title',
    initialState: '',
    help: 'Native tooltip shown on hover, e.g. the full text when the tag is clipped.'
  },
  action: {
    type: 'list' as const,
    title: 'Action',
    options: listOptions<ActionPreset>({
      none: 'None',
      button: 'Button',
      internalLink: 'Internal link',
      externalLink: 'External link'
    }),
    initialState: 'none' as const,
    help: 'Button and links render with hover and press states. An internal link leaves the frame (_top), an external one opens in a new tab (_blank).'
  }
} satisfies PanelConfigFor<typeof CmkTag, 'action'> & {
  action: ListPropDef<ActionPreset>
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
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import { computed } from 'vue'

import UclCmkTagDev from './UclCmkTagDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkTag, 'action'>().createRef(panelConfig)

const action = computed(() => actionPresets[propState.value.action])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkTag</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkTag
        :content="propState.content"
        :value="propState.value || undefined"
        :size="propState.size"
        :color="propState.color"
        :variant="propState.variant"
        :spacing="propState.spacing"
        :action="action"
      />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkTagDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
