<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

interface AvailableWidgetProps {
  label: TranslatedString
  icon: SimpleIcons
  disabled?: boolean
}

defineProps<AvailableWidgetProps>()
</script>

<template>
  <div class="db-available-widget__item">
    <div class="db-available-widget__item-icon">
      <CmkIcon :name="icon" size="xxlarge" :colored="!disabled" />
    </div>
    <div
      class="db-available-widget__item-label"
      :class="disabled ? 'db-available-widget__item-label-disabled' : ''"
    >
      <CmkLabel>{{ label }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.db-available-widget__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  max-width: 72px;
  text-align: center;
}

.db-available-widget__item-icon {
  display: block;
}

.db-available-widget__item-label {
  display: block;
  overflow-wrap: break-word;
}

.db-available-widget__item-label-disabled {
  color: var(--ux-theme-10);
}
</style>
