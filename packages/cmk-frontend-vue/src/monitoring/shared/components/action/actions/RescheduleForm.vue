<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface RescheduleValues {
  spreadMinutes: number | undefined
}
</script>

<script setup lang="ts">
import { watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const model = defineModel<RescheduleValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

watch(
  () => model.value.spreadMinutes,
  (minutes) => emit('update:valid', minutes !== undefined && minutes >= 0),
  { immediate: true }
)
</script>

<template>
  <div class="monitoring-reschedule-form">
    <p class="monitoring-reschedule-form__intro">
      {{ _t('Execution will be spread across a custom time period.') }}
    </p>

    <label class="monitoring-reschedule-form__field">
      <span class="monitoring-reschedule-form__label">
        {{ _t('Spread over') }}<CmkLabelRequired :show="true" space="before" />
        <CmkHelpText
          :help="
            _t(
              'Distributes the rescheduled checks across the specified number of minutes, ' +
                'preventing a load spike on your monitoring server. Enter the number of minutes ' +
                'over which the checks should be spread.'
            )
          "
        />
      </span>
      <CmkInput
        v-model="model.spreadMinutes"
        type="number"
        field-size="SMALL"
        :unit="_t('minutes')"
      />
    </label>
  </div>
</template>

<style scoped>
.monitoring-reschedule-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-reschedule-form__intro {
  margin: 0;
  color: var(--font-color-dimmed);
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
