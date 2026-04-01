<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type PanelConfig } from '@ucl/_ucl/components/detail-page'

export const a11yData = [
  {
    keys: ['HTML Lang Attribute'],
    description:
      'When switching languages dynamically, ensure the root `<html>` element’s `lang` attribute is updated (e.g., `lang="de"`). This is critical for screen readers to load the correct pronunciation dictionary.'
  }
]
export const codeExample = `<script setup lang="ts">
import usei18n from '@/lib/i18n'
${'import'} CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t, _tn } = usei18n()
<${'/'}script>

<template>
  <CmkParagraph>{{ _t('Hello %{name}!', { name: 'Alice' }) }}</CmkParagraph>
</template>`
export const panelConfig = {
  language: {
    type: 'list',
    title: 'Active Language',
    options: [
      { title: 'English', name: 'en' },
      { title: 'German', name: 'de' },
      { title: 'French', name: 'fr' }
    ],
    initialState: 'en'
  },
  name: {
    type: 'string',
    title: 'Name',
    initialState: 'Alice',
    help: 'Enter a name to see interpolation in action.'
  },
  appleCount: {
    type: 'list',
    title: 'Apple Count',
    options: [
      { title: '0 Apples', name: '0' },
      { title: '1 Apple', name: '1' },
      { title: '3 Apples', name: '3' }
    ],
    help: 'Select the number of apples to see pluralization in action.',
    initialState: '0'
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
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkSpace from '@/components/CmkSpace.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import translatedStringFromTS from './_ts_file_using_i18n'

defineProps<{ screenshotMode: boolean }>()

const { _t, _tn, switchLanguage, translationLoading } = usei18n()

const propState = ref(createPanelState(panelConfig))

watch(
  () => propState.value.language,
  (newLang) => {
    if (newLang) {
      void switchLanguage(String(newLang))
    }
  },
  { immediate: true }
)
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>I18n</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div style="display: flex; flex-direction: column">
        <CmkParagraph>
          <strong>Status: </strong>
          {{ translationLoading ? _t('Loading translations...') : _t('Translations loaded') }}
        </CmkParagraph>

        <CmkSpace size="small" direction="vertical" />

        <CmkParagraph>
          <strong>Interpolation: </strong>
          {{ _t('Hello %{name}!', { name: propState.name }) }}
        </CmkParagraph>
        <CmkSpace size="small" direction="vertical" />
        <CmkParagraph>
          <strong>Pluralization: </strong>
          {{
            _tn('There is %{ n } apple', 'There are %{ n } apples', Number(propState.appleCount), {
              n: propState.appleCount ?? 0
            })
          }}
        </CmkParagraph>
        <CmkSpace size="small" direction="vertical" />
        <CmkParagraph>
          <strong>From TS File: </strong>
          {{ translatedStringFromTS }}
        </CmkParagraph>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
