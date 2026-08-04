<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from 'cmk-ui-library/components/CmkIcon/types'

import type { HostMode } from '@/monitoring/shared/api/types'

defineProps<{
  modes: HostMode[]
}>()
</script>

<template>
  <div class="monitoring-host-mode-icons">
    <a
      v-for="mode in modes"
      :key="mode.icon_name"
      class="monitoring-host-mode-icons__link"
      :href="mode.link"
      :title="mode.title"
      target="_top"
    >
      <CmkIcon :name="mode.icon_name as SimpleIcons" :title="mode.title" size="medium" />
    </a>
  </div>
</template>

<style scoped>
.monitoring-host-mode-icons {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-2);
}

.monitoring-host-mode-icons__link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}
</style>
