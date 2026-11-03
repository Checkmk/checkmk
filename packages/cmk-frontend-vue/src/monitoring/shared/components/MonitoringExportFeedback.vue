<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { RowExportFeedback } from '@/monitoring/shared/export/useRowExport'

const { _t } = usei18n()

const feedback = defineModel<RowExportFeedback | null>({ required: true })
</script>

<template>
  <CmkAlert
    v-if="feedback?.variant === 'loading'"
    variant="loading"
    class="monitoring-export-feedback"
    :text="feedback.text"
  />
  <CmkAlert
    v-else-if="feedback"
    :variant="feedback.variant"
    class="monitoring-export-feedback"
    :text="feedback.text"
    :optional-button="{
      title: _t('Dismiss'),
      icon: 'cancel',
      onclick: () => (feedback = null)
    }"
  />
</template>

<style scoped>
.monitoring-export-feedback {
  flex: 0 0 auto;
  margin: var(--spacing-half) 0 0;
}
</style>
