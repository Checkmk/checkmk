<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

interface Props {
  isActive: boolean
}
defineProps<Props>()
</script>

<template>
  <CmkMultitoneIcon
    v-if="isActive"
    name="check-circle"
    :primary-color="{ custom: 'var(--db-filter-selection-active-icon-color)' }"
    class="db-filter-selection-active-icon"
  />
  <span v-else class="db-filter-selection-active-icon" />
</template>

<style scoped>
.db-filter-selection-active-icon {
  width: var(--dimension-6);
  height: var(--dimension-6);
  min-width: var(--dimension-6);
  min-height: var(--dimension-6);
  display: inline-block;
  flex-shrink: 0;

  --db-filter-selection-active-icon-color: var(--color-corporate-green-70);
}

body[data-theme='modern-dark'] .db-filter-selection-active-icon {
  --db-filter-selection-active-icon-color: var(--color-corporate-green-50);
}
</style>
