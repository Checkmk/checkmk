<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'

import type { MonitoringIcon } from '@/monitoring/shared/api/types'

defineProps<{
  icons: MonitoringIcon[]
}>()
</script>

<template>
  <div class="monitoring-icon-list">
    <component
      :is="icon.link ? 'a' : 'span'"
      v-for="icon in icons"
      :key="icon.icon_name"
      class="monitoring-icon-list__item"
      :href="icon.link"
      :target="icon.link ? '_top' : undefined"
      :title="icon.title"
    >
      <CmkIcon :name="icon.icon_name as SimpleIcons" :title="icon.title" size="medium" />
    </component>
  </div>
</template>

<style scoped>
.monitoring-icon-list {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-2);
}

.monitoring-icon-list__item {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}
</style>
