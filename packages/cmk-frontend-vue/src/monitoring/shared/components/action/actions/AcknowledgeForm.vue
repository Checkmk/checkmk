<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import type { ZonedDateTime } from '@internationalized/date'

export interface AcknowledgeValues {
  comment: string
  expireOnEnabled: boolean
  expireOn: ZonedDateTime | null
  sticky: boolean
  persistent: boolean
  notify: boolean
}

export function isAcknowledgeValid(values: AcknowledgeValues): boolean {
  const expiryValid = !values.expireOnEnabled || values.expireOn !== null
  return values.comment.trim() !== '' && expiryValid
}
</script>

<script setup lang="ts">
import CmkDateTimePicker from 'cmk-ui-library/components/date-time/CmkDateTimePicker.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { watch } from 'vue'

const model = defineModel<AcknowledgeValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

watch(model, (values) => emit('update:valid', isAcknowledgeValid(values)), {
  immediate: true,
  deep: true
})
</script>

<template>
  <div class="monitoring-acknowledge-form">
    <div class="monitoring-acknowledge-form__section">
      <label class="monitoring-acknowledge-form__field">
        <span class="monitoring-acknowledge-form__label">
          {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
        </span>
        <CmkInput
          v-model="model.comment"
          field-size="large"
          :placeholder="_t('Enter a comment…')"
        />
      </label>
    </div>

    <div class="monitoring-acknowledge-form__section">
      <div class="monitoring-acknowledge-form__field">
        <CmkCheckbox
          v-model="model.expireOnEnabled"
          :label="_t('Expire on')"
          :help="
            _t(
              'Let the acknowledgement expire automatically. Leave this off to keep it until the ' +
                'host recovers or it is removed manually.'
            )
          "
        />
        <CmkDateTimePicker
          v-if="model.expireOnEnabled"
          v-model="model.expireOn"
          :nullable="true"
          :label="_t('Choose an expiry date & time')"
        />
      </div>

      <CmkCheckbox
        v-model="model.sticky"
        :label="_t('Ignore status changes until the host recovers (OK/UP)')"
      />
      <CmkCheckbox v-model="model.persistent" :label="_t('Persistent comment')" />
      <CmkCheckbox v-model="model.notify" :label="_t('Notify affected users')" />
    </div>
  </div>
</template>

<style scoped>
.monitoring-acknowledge-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-acknowledge-form__section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-acknowledge-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-acknowledge-form__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  font-weight: var(--font-weight-bold);
}
</style>
