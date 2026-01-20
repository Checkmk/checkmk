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
  <div class="db-available-widget__item" :class="{ 'db-available-widget__item-button': !disabled }">
    <div class="db-available-widget__item-icon">
      <CmkIcon :name="icon" size="xxlarge" :colored="!disabled" />
    </div>
    <div
      class="db-available-widget__item-label"
      :class="disabled ? 'db-available-widget__item-label-disabled' : ''"
    >
      <CmkLabel cursor="pointer">{{ label }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.db-available-widget__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-4);
  max-width: 72px;
  text-align: center;
  height: 80%;
}

.db-available-widget__item-button {
  cursor: pointer;
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--dimension-4);

  &:hover {
    background-color: rgb(from var(--default-form-element-bg-color) r g b / 60%);
  }
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
