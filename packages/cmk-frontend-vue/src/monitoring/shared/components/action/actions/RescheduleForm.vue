<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface RescheduleValues {
  spreadMinutes: number | undefined
}

function hasSpread(values: RescheduleValues): boolean {
  return values.spreadMinutes !== undefined && values.spreadMinutes >= 0
}
</script>

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkHelpText from 'cmk-ui-library/components/CmkHelpText.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject, watch } from 'vue'

import { ACTION_TARGET_COUNT } from '../types'

const props = withDefaults(
  defineProps<{
    /** Whether to point out the fields that keep the form from being submitted. */
    showErrors?: boolean
  }>(),
  { showErrors: false }
)

const model = defineModel<RescheduleValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

const targetCount = inject(
  ACTION_TARGET_COUNT,
  computed(() => 1)
)

const spreadErrors = computed(() =>
  props.showErrors && !hasSpread(model.value) ? [_t('Enter 0 or more minutes.')] : []
)

watch(model, (values) => emit('update:valid', hasSpread(values)), {
  immediate: true,
  deep: true
})
</script>

<template>
  <div class="monitoring-reschedule-form">
    <CmkAlert
      v-if="targetCount > 1"
      variant="warning"
      :text="
        _t(
          'Rescheduling %{count} checks at once puts extra load on the monitoring server and the ' +
            'monitored hosts. Spread the execution over a longer period to soften the peak.',
          { count: targetCount }
        )
      "
    />

    <div class="monitoring-reschedule-form__section">
      <label class="monitoring-reschedule-form__field">
        <span class="monitoring-reschedule-form__label">
          {{ _t('Spread over') }}<CmkLabelRequired :show="true" space="before" />
          <CmkHelpText
            :help="_t('Enter the number of minutes over which the checks should be spread.')"
          />
        </span>
        <CmkInput
          v-model="model.spreadMinutes"
          type="number"
          field-size="small"
          :unit="_t('minutes')"
          :external-errors="spreadErrors"
        />
      </label>
    </div>
  </div>
</template>

<style scoped>
.monitoring-reschedule-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-reschedule-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-reschedule-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-reschedule-form__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  font-weight: var(--font-weight-bold);
}
</style>
