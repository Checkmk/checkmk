<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { DynamicIcon } from 'cmk-shared-typing/typescript/icon'

import CmkDynamicIcon from '@/components/CmkIcon/CmkDynamicIcon/CmkDynamicIcon.vue'

import { getIconId } from './utils'

interface IconGalleryProps {
  icons: DynamicIcon[]
  displayNames?: boolean
}

interface IconGalleryEmit {
  selectIcon: [DynamicIcon]
}

defineProps<IconGalleryProps>()
const emit = defineEmits<IconGalleryEmit>()
</script>

<template>
  <div v-if="displayNames" class="db-icon-gallery__grid">
    <div v-for="(icon, index) in icons" :key="index" class="db-icon-gallery__inline-wrapper">
      <CmkDynamicIcon
        :title="getIconId(icon)!"
        :spec="icon"
        size="xlarge"
        @click="emit('selectIcon', icon)"
      />
      <span>{{ getIconId(icon) }}</span>
    </div>
  </div>

  <div v-else class="db-icon-gallery__flex-container">
    <CmkDynamicIcon
      v-for="(icon, index) in icons"
      :key="index"
      class="db-icon-gallery__flex-item"
      :title="getIconId(icon)!"
      :spec="icon"
      size="xlarge"
      @click="emit('selectIcon', icon)"
    />
  </div>
</template>

<style scoped>
.db-icon-gallery__flex-container {
  display: flex;
  flex-flow: row wrap;
  justify-content: flex-start;
  gap: var(--dimension-4);
}

.db-icon-gallery__flex-item {
  cursor: pointer;
  white-space: nowrap;
}

.db-icon-gallery__inline-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.db-icon-gallery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  grid-auto-columns: max-content;
  grid-auto-flow: row;
  grid-auto-rows: max-content;
  gap: 8px;
}
</style>
