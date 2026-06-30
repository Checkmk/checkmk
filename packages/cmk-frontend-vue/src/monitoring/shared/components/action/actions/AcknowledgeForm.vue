<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
import type { ZonedDateTime } from '@internationalized/date'

export interface AcknowledgeValues {
  comment: string
  expireOn: ZonedDateTime | null
  sticky: boolean
  persistent: boolean
  notify: boolean
}
</script>

<script setup lang="ts">
import { watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkDateTimePicker from '@/components/date-time/CmkDateTimePicker.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const model = defineModel<AcknowledgeValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

watch(
  () => model.value.comment,
  (comment) => emit('update:valid', comment.trim() !== ''),
  { immediate: true }
)
</script>

<template>
  <div class="monitoring-acknowledge-form">
    <label class="monitoring-acknowledge-form__field">
      <span class="monitoring-acknowledge-form__label">
        {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
      </span>
      <CmkInput v-model="model.comment" field-size="large" :placeholder="_t('Enter a comment…')" />
    </label>

    <div class="monitoring-acknowledge-form__field">
      <span class="monitoring-acknowledge-form__label">
        {{ _t('Expire on') }}
        <CmkHelpText
          :help="
            _t(
              'Optionally let the acknowledgement expire automatically. Leave empty to keep it ' +
                'until the host recovers or it is removed manually.'
            )
          "
        />
      </span>
      <CmkDateTimePicker
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
</template>

<style scoped>
.monitoring-acknowledge-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
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
