<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface FakeCheckResultValues {
  state: number
  pluginOutput: string
  metrics: string
}
</script>

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkRadioButton from 'cmk-ui-library/components/user-input/CmkRadioButton/CmkRadioButton.vue'
import CmkRadioGroup from 'cmk-ui-library/components/user-input/CmkRadioButton/CmkRadioGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ActionTargetKind } from '../types'

const props = defineProps<{ targetKind: ActionTargetKind }>()

const model = defineModel<FakeCheckResultValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

// Every result is a valid one; the plug-in output defaults to who set which state.
emit('update:valid', true)

const states = computed(() =>
  props.targetKind === 'host'
    ? [_t('Up'), _t('Down')]
    : [_t('OK'), _t('Warning'), _t('Critical'), _t('Unknown')]
)

const state = computed({
  get: () => String(model.value.state),
  set: (value: string) => (model.value.state = Number(value))
})
</script>

<template>
  <div class="monitoring-fake-check-result-form">
    <CmkAlert
      variant="warning"
      :text="
        _t(
          'If you are looking for a way to test your notification settings, try \'Test notification\' in Setup > Test notifications'
        )
      "
    />
    <div class="monitoring-fake-check-result-form__section">
      <span class="monitoring-fake-check-result-form__label">{{ _t('Result') }}</span>
      <CmkRadioGroup v-model="state" :label="_t('Result')">
        <CmkRadioButton
          v-for="(title, index) in states"
          :key="index"
          :value="String(index)"
          :label="title"
        />
      </CmkRadioGroup>
      <label class="monitoring-fake-check-result-form__field">
        <span class="monitoring-fake-check-result-form__label">{{ _t('Plug-in output') }}</span>
        <CmkInput
          v-model="model.pluginOutput"
          field-size="large"
          :placeholder="_t('What is the purpose?')"
        />
      </label>
      <label class="monitoring-fake-check-result-form__field">
        <span class="monitoring-fake-check-result-form__label">{{ _t('Metrics') }}</span>
        <CmkInput
          v-model="model.metrics"
          field-size="large"
          :placeholder="_t('Enter metrics to show in notifications etc. ...')"
        />
      </label>
    </div>
  </div>
</template>

<style scoped>
.monitoring-fake-check-result-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-fake-check-result-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-fake-check-result-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-fake-check-result-form__label {
  font-weight: var(--font-weight-bold);
}
</style>
