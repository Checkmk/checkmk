<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkTabs from '../CmkTabs/CmkTabs.vue'
import CmkTab from '../CmkTabs/CmkTab.vue'
import type { CmkIconProps } from '../CmkIcon.vue'
import CmkTabContent from '../CmkTabs/CmkTabContent.vue'
import CmkIcon from '../CmkIcon.vue'
import { ref } from 'vue'

const openedTab = ref<string | number>('tab-3')

const tabs: {
  id: string
  disabled?: boolean
  title: string
  icon: CmkIconProps
  content: string
}[] = [
  {
    id: 'tab-1',
    title: 'Tab 1',
    icon: {
      name: 'search'
    },
    content: 'Any content'
  },
  {
    id: 'tab-2',
    title: 'Tab 2 (disabled)',
    disabled: true,
    icon: {
      name: 'close'
    },
    content: 'Any content Tab 2'
  },
  {
    id: 'tab-3',
    title: 'Tab 3 (long title)',
    icon: {
      name: 'info-circle'
    },
    content: 'Any content Tab 3'
  }
]

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkTabs v-model="openedTab">
    <template #tabs>
      <CmkTab
        v-for="tab in tabs"
        :id="tab.id"
        :key="tab.id"
        :disabled="tab.disabled"
        class="cmk-demo-tabs"
      >
        <CmkIcon :name="tab.icon.name"></CmkIcon>
        <h2>{{ tab.title }}</h2>
      </CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
        <p>{{ tab.content }}</p>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>

<style scoped>
.cmk-demo-tabs {
  display: flex;
  flex-direction: row;
  align-items: center;
  > h2 {
    margin: 0;
    padding: 0;
  }
  > .cmk-icon {
    margin-right: 16px;
  }
}
</style>
