<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkSpace from '@/components/CmkSpace.vue'

export type StatusType = 'OK' | 'WARNING' | 'DANGER' | 'INFO' | null

interface StatusMessageProps {
  status?: StatusType
  topic?: TranslatedString
  text: TranslatedString
  linkedText?: TranslatedString
}

interface StatusMessageEmits {
  click: []
}

defineProps<StatusMessageProps>()
defineEmits<StatusMessageEmits>()

const bullet: string = '●'
</script>

<template>
  <div class="db-status-message__container">
    <template v-if="topic">
      <strong>{{ topic }}:</strong>
      <CmkSpace />
    </template>
    <template v-if="status">
      <span
        class="db-status-message__bullet"
        :class="status ? `db-status-message__bullet-${status.toLowerCase()}` : ''"
        >{{ bullet }}</span
      >
      <CmkSpace />
    </template>
    <span>{{ text }}</span>
    <template v-if="linkedText">
      <CmkSpace />
      <a href="#" @click.prevent="$emit('click')">{{ linkedText }}</a>
    </template>
  </div>
</template>

<style scoped>
.db-status-message__container {
  padding: var(--dimension-4) var(--dimension-6);
  border-radius: var(--dimension-3);
  background-color: var(--ux-theme-0);
}

.db-status-message__bullet-ok {
  color: var(--popup-dialog-success);
}

.db-status-message__bullet-warning {
  color: var(--popup-dialog-warning);
}

.db-status-message__bullet-danger {
  color: var(--popup-dialog-danger);
}

.db-status-message__bullet-info {
  color: var(--popup-dialog-info);
}
</style>
