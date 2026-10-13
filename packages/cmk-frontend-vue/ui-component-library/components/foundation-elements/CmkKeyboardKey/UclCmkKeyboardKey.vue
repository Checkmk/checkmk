<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfigFor, listOptions } from '@ucl/_ucl/components/detail-page'
import type { CmkKeyboardKeyProps, Sizes } from 'cmk-ui-library/components/CmkKeyboardKey.vue'

import codeExample from './UclCmkKeyboardKeyCodeExample.vue?raw'

export const panelConfig = {
  keyboardKey: {
    type: 'list' as const,
    title: 'Key Content',
    options: listOptions<CmkKeyboardKeyProps['keyboardKey']>({
      'arrow-left': 'Arrow Left',
      'arrow-right': 'Arrow Right',
      'arrow-up': 'Arrow Up',
      'arrow-down': 'Arrow Down',
      enter: 'Enter',
      backspace: 'Backspace',
      Ctrl: 'Ctrl',
      Shift: 'Shift',
      A: 'A'
    }),
    help: 'Custom keys can be added by passing any string value. For example, passing "Ctrl,Shift,A" will render a key with the text inside.',
    initialState: 'enter' as const
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
  }
} satisfies PanelConfigFor<typeof CmkKeyboardKey>
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
import CmkKeyboardKey from 'cmk-ui-library/components/CmkKeyboardKey.vue'

import UclCmkKeyboardKeyDev from './UclCmkKeyboardKeyDev.vue'

defineProps<{ screenshotMode: boolean }>()

const propState = new PanelStateCreator<typeof CmkKeyboardKey>().createRef(panelConfig)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkKeyboardKey</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkKeyboardKey :keyboard-key="propState.keyboardKey" :size="propState.size" />

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />

    <UclDetailPageDeveloperPlayground>
      <UclCmkKeyboardKeyDev :screenshot-mode="screenshotMode" />
    </UclDetailPageDeveloperPlayground>
  </UclDetailPageLayout>
</template>
