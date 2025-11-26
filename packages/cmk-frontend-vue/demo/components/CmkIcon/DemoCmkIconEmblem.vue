<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkIcon, { type IconSizeNames } from '@/components/CmkIcon'
import CmkIconEmblem from '@/components/CmkIcon/CmkIconEmblem.vue'
import { emblems } from '@/components/CmkIcon/icons.constants'
import type { IconEmblems, SimpleIcons } from '@/components/CmkIcon/types'

const icon = ref<SimpleIcons>('filter')
const emblem = ref<IconEmblems>('warning')

const sizes: IconSizeNames[] = [
  'xxsmall',
  'xsmall',
  'small',
  'medium',
  'large',
  'xlarge',
  'xxlarge',
  'xxxlarge'
]

const SOME_ICONS: Array<SimpleIcons> = [
  'info-circle',
  'validation-error',
  'disabled',
  'enabled',
  'crit-problem',
  'checkmk-logo-min',
  'export-link',
  'delete',
  'search',
  'checkmark-bare',
  'back',
  'continue',
  'save-to-services',
  'insertdate',
  'alert-crit',
  'alert-warn',
  'alert-up',
  'about-checkmk',
  'check',
  'cross',
  'save',
  'cancel',
  'pending-task',
  'sparkle',
  'history',
  'main-changes',
  'main-setup-active',
  'main-monitoring-active',
  'main-customize-active',
  'menu',
  'info'
]

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <pre>
&lt;!-- no whitespace between CmkIconEmblem and CmkIcon! --&gt;
&lt;CmkIconEmblem emblem="warning"&gt;&lt;CmkIcon name="filter" size="medium" /&gt;&lt;/CmkIconEmblem&gt;
  </pre>
  <select v-model="icon">
    <option v-for="i in SOME_ICONS" :key="i">{{ i }}</option>
  </select>
  <select v-model="emblem">
    <option :value="undefined">undefined</option>
    <option v-for="e in emblems" :key="e">{{ e }}</option>
  </select>
  <ul>
    <li v-for="size in sizes" :key="size || 'default'" class="demo-cmk-icon__element-entry">
      <CmkIconEmblem :emblem="emblem"
        ><CmkIcon :name="icon" :size="size" title="sometitle"
      /></CmkIconEmblem>
      ({{ size }})
    </li>
  </ul>
</template>

<style scoped>
ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin: 1em;
}
</style>
