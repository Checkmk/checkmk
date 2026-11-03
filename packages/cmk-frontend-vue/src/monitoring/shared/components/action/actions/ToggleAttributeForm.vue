<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface ToggleAttributeValues {
  enabled: boolean
}
</script>

<script setup lang="ts">
import CmkRadioButton from 'cmk-ui-library/components/user-input/CmkRadioButton/CmkRadioButton.vue'
import CmkRadioGroup from 'cmk-ui-library/components/user-input/CmkRadioButton/CmkRadioGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

defineProps<{ label: TranslatedString }>()

const model = defineModel<ToggleAttributeValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

emit('update:valid', true)

const choice = computed({
  get: () => (model.value.enabled ? 'enable' : 'disable'),
  set: (value: string) => (model.value.enabled = value === 'enable')
})
</script>

<template>
  <div class="monitoring-toggle-attribute-form">
    <span class="monitoring-toggle-attribute-form__label">{{ label }}</span>
    <CmkRadioGroup v-model="choice" :label="label" orientation="horizontal">
      <CmkRadioButton value="enable" :label="_t('Enable')" />
      <CmkRadioButton value="disable" :label="_t('Disable')" />
    </CmkRadioGroup>
  </div>
</template>

<style scoped>
.monitoring-toggle-attribute-form {
  display: flex;
  align-items: center;
  gap: var(--dimension-7);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-toggle-attribute-form__label {
  font-weight: var(--font-weight-bold);
}
</style>
