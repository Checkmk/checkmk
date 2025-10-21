<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkDropdown from '@/components/CmkDropdown'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type {
  CmkIconSize,
  CmkMultitoneIconColor,
  CmkMultitoneIconNames
} from '@/components/CmkIcon/types.ts'

defineProps<{ screenshotMode: boolean }>()

const icon = ref<CmkMultitoneIconNames>('services')
const iconSuggestions = [
  { name: 'services', title: 'services' },
  { name: 'aggr', title: 'aggr' }
]

const size = ref<CmkIconSize>('xxlarge')
const sizeSuggestions = [
  { name: 'xsmall', title: 'xsmall' },
  { name: 'small', title: 'small' },
  { name: 'medium', title: 'medium' },
  { name: 'large', title: 'large' },
  { name: 'xlarge', title: 'xlarge' },
  { name: 'xxlarge', title: 'xxlarge' },
  { name: 'xxxlarge', title: 'xxxlarge' }
]

const primaryTone = ref<CmkMultitoneIconColor>('success')
const secondaryTone = ref<CmkMultitoneIconColor>('success')
const toneSuggestions = [
  { name: 'customization', title: 'customization' },
  { name: 'danger', title: 'danger' },
  { name: 'hosts', title: 'hosts' },
  { name: 'info', title: 'info' },
  { name: 'others', title: 'others' },
  { name: 'services', title: 'services' },
  { name: 'specialAgents', title: 'specialAgents' },
  { name: 'success', title: 'success' },
  { name: 'users', title: 'users' },
  { name: 'warning', title: 'warning' }
]
</script>

<template>
  <div>
    <label>Icon:</label>
    <CmkDropdown
      v-model:selected-option="icon as string"
      :options="{
        type: 'fixed',
        suggestions: iconSuggestions
      }"
      component-id="icon"
      label="Icon to render"
    />
  </div>
  <div>
    <label>Size:</label>
    <CmkDropdown
      v-model:selected-option="size as string"
      :options="{
        type: 'fixed',
        suggestions: sizeSuggestions
      }"
      component-id="size"
      label="Icon size"
    />
  </div>
  <div>
    <label>Primary color:</label>
    <CmkDropdown
      v-model:selected-option="primaryTone as string"
      :options="{
        type: 'fixed',

        suggestions: toneSuggestions
      }"
      component-id="primary-tone"
      label="Primary icon color"
    />
  </div>

  <div>
    <label>Secondary color:</label>
    <CmkDropdown
      v-model:selected-option="secondaryTone as string"
      :options="{
        type: 'fixed',

        suggestions: toneSuggestions
      }"
      component-id="secondary-tone"
      label="Secondary icon color"
    />
  </div>

  <div class="demo-cmk-multitone-icon">
    <CmkMultitoneIcon
      :name="icon"
      :primary-color="primaryTone"
      :secondary-color="secondaryTone"
      :size="size"
    ></CmkMultitoneIcon>
  </div>
</template>

<style scoped>
.demo-cmk-multitone-icon {
  width: 100%;
  height: auto;
  display: flex;
  justify-content: center;
  padding: 40px 0 0;
  box-sizing: border-box;
}

div:has(> label) {
  padding: 8px 0;
}

label {
  width: 200px;
  display: inline-block;
}
</style>
