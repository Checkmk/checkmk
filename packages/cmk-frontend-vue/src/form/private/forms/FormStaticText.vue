<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { StaticText } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

import FormLabel from '@/form/private/FormLabel.vue'

const props = defineProps<{
  spec: StaticText
  // Kept for dispatcher symmetry; StaticText never validates.
  backendValidation: unknown[]
}>()

// The displayed text comes from the v-model. The List visitor shares one
// schema across all entries (built from `DEFAULT_VALUE`), so `spec.value`
// is always the empty fallback for list rows — only `data` carries the
// per-instance text. The v-model also round-trips the value back on submit
// so the parent form preserves it.
const data = defineModel<unknown>('data', { required: true })
const display = computed(() => (typeof data.value === 'string' ? data.value : ''))

const ALERT_VARIANTS = {
  alert_info: 'info',
  alert_warning: 'warning',
  alert_error: 'error'
} as const
const alertVariant = computed(
  () => ALERT_VARIANTS[props.spec.style as keyof typeof ALERT_VARIANTS] ?? null
)
</script>

<template>
  <CmkAlertBox v-if="alertVariant" size="small" :variant="alertVariant">{{ display }}</CmkAlertBox>
  <pre v-else-if="spec.style === 'preformatted'" class="vs_fixed_value">{{ display }}</pre>
  <FormLabel v-else>{{ display }}</FormLabel>
</template>
