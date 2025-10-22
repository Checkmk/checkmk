<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeMount, ref } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import { dashboardAPI } from '@/dashboard-wip/utils'

const { _t } = usei18n()

const showInMonitorMenu = defineModel<boolean>('showInMonitorMenu', { required: true })
const selectedTopic = defineModel<string>('selectedTopic', { default: '' })

const topics = ref<Suggestion[]>([])

onBeforeMount(async () => {
  const apiTopics = await dashboardAPI.listMainMenuTopics()
  apiTopics.sort((a, b) => a.sortIndex - b.sortIndex)
  topics.value = apiTopics.map((item) => ({
    name: item.id,
    title: untranslated(item.title)
  }))
  if (selectedTopic.value === '') {
    const defaultTopic = apiTopics.find((t) => t.isDefault)
    if (defaultTopic) {
      selectedTopic.value = defaultTopic.id
    }
  }
})
</script>

<template>
  <CmkCheckbox v-model="showInMonitorMenu" :label="_t('Show in monitor menu')" />
  <CmkIndent v-if="showInMonitorMenu">
    <CmkDropdown
      :selected-option="selectedTopic"
      :label="_t('Select option')"
      :options="{
        type: 'fixed',
        suggestions: topics
      }"
      @update:selected-option="(value) => (selectedTopic = value || selectedTopic)"
    />
  </CmkIndent>
</template>
