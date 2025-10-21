<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkProgressbar from '@/components/CmkProgressbar.vue'

const { _t } = usei18n()

defineProps<{
  activatingOnSites: string[] | string | undefined
}>()
</script>

<template>
  <div class="mm-changes-activating__container">
    <span v-if="typeof activatingOnSites === 'string'" class="mm-changes-activating__text"
      >{{ _t('Activating changes on ') }}
      {{ "'".concat(activatingOnSites as string).concat("'...") }}</span
    >
    <span v-else class="mm-changes-activating__text">{{ _t('Activating changes... ') }} </span>
    <span>{{ _t("You can safely navigate away - we'll keep working in the background") }}</span>
    <CmkProgressbar max="unknown"></CmkProgressbar>
  </div>
</template>

<style scoped>
.mm-changes-activating__container {
  display: flex;
  padding: var(--dimension-9) var(--dimension-4);
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--dimension-4);
  align-self: stretch;
  background: var(--ux-theme-4);
  border-radius: var(--border-radius);
}

.mm-changes-activating__text {
  font-weight: var(--font-weight-bold);
}
</style>
