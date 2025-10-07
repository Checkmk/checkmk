<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

interface WidgetButtonProps {
  icon: string
  label: TranslatedString
  disabled?: boolean
  selected?: boolean
}

defineProps<WidgetButtonProps>()
defineEmits<{
  click: [event: MouseEvent]
}>()
</script>

<template>
  <button
    :class="!!selected ? 'db-widget-button' : ''"
    :disabled="!!disabled"
    @click="$emit('click', $event)"
  >
    <div>
      <CmkIcon :name="icon" />
    </div>
    <div>
      <CmkLabel>{{ label }}</CmkLabel>
    </div>
  </button>
</template>

<style scoped>
.db-widget-button {
  border-color: var(--success);
}
</style>
