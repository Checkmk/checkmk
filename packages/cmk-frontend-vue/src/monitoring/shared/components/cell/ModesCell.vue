<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import type { SimpleIcons } from '@/components/CmkIcon/types'

import type { HostMode } from '../../api/types'
import BaseCell from './BaseCell.vue'

defineProps<{
  modes: HostMode[]
  columnId?: string | undefined
}>()
</script>

<template>
  <BaseCell :column-id="columnId">
    <template #default>
      <div class="monitoring-modes-cell">
        <a
          v-for="mode in modes"
          :key="mode.icon_name"
          class="monitoring-modes-cell__link"
          :href="mode.link"
          :title="mode.title"
          target="_top"
        >
          <CmkIcon :name="mode.icon_name as SimpleIcons" :title="mode.title" size="medium" />
        </a>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-modes-cell {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-2);
}

.monitoring-modes-cell__link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}
</style>
