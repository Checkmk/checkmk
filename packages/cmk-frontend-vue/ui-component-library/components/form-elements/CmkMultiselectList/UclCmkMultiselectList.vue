<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import codeExample from './UclCmkMultiselectListCodeExample.vue?raw'

export const a11yData = [
  {
    keys: ['Tab'],
    description: 'Moves keyboard focus to the search field, then from checkbox to checkbox.'
  },
  {
    keys: [['Shift', 'Tab']],
    description: 'Moves focus back to the previous checkbox or the search field.'
  },
  {
    keys: ['Space'],
    description: 'Selects or deselects the focused item.'
  }
]
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkMultiselectList from 'cmk-ui-library/components/user-input/CmkMultiselectList.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const items = [
  'State',
  'Host',
  'Relations',
  'Host alias',
  'IP address',
  'Folder',
  'Site',
  'Check age',
  'State age',
  'Labels',
  'Tags'
].map((title) => ({ name: title.toLowerCase().replace(/ /g, '_'), title: untranslated(title) }))

const selected = ref(['state', 'host', 'host_alias', 'site', 'check_age', 'state_age'])
const fewSelected = ref(['state'])
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkMultiselectList</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div>
        <CmkParagraph>From nine items on, the list is searchable and scrolls.</CmkParagraph>
        <CmkMultiselectList
          v-model="selected"
          :items="items"
          :label="untranslated('Columns')"
          :empty-text="untranslated('No matching columns')"
        />
        <CmkParagraph>Selected: {{ selected.join(', ') || '—' }}</CmkParagraph>
        <CmkParagraph>With fewer items, the list hugs them.</CmkParagraph>
        <CmkMultiselectList
          v-model="fewSelected"
          :items="items.slice(0, 3)"
          :label="untranslated('Columns')"
        />
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>
