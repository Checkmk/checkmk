<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import { type CmkIconVariants } from '@/components/CmkIcon'
import CmkIconWithEmblem from '@/components/CmkIcon/CmkIconWithEmblem.vue'
import { emblems, simpleIcons } from '@/components/CmkIcon/icons.constants'
import type { IconEmblems, SimpleIcons } from '@/components/CmkIcon/types'

const icon = ref<SimpleIcons>('filter')
const emblem = ref<IconEmblems>('warning')

const sizes: CmkIconVariants['size'][] = [
  'xxsmall',
  'xsmall',
  'small',
  'medium',
  'large',
  'xlarge',
  'xxlarge',
  'xxxlarge'
]

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <select v-model="icon">
    <option v-for="i in simpleIcons" :key="i">{{ i }}</option>
  </select>
  <select v-model="emblem">
    <option :value="undefined">undefined</option>
    <option v-for="e in emblems" :key="e">{{ e }}</option>
  </select>
  <ul>
    <li v-for="size in sizes" :key="size || 'default'" class="demo-cmk-icon__element-entry">
      <CmkIconWithEmblem :icon="icon" :icon-emblem="emblem" :size="size" title="sometitle" />
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
