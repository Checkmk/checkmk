<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface CustomNotificationValues {
  comment: string
  forced: boolean
  broadcast: boolean
}
</script>

<script setup lang="ts">
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

import type { ActionTargetKind } from '../types'

const props = withDefaults(
  defineProps<{
    targetKind: ActionTargetKind
    /** Whether to point out the fields that keep the form from being submitted. */
    showErrors?: boolean
  }>(),
  { showErrors: false }
)

const model = defineModel<CustomNotificationValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

const commentErrors = computed(() =>
  props.showErrors && model.value.comment.trim() === '' ? [_t('Comment is required.')] : []
)

watch(
  () => model.value.comment,
  (comment) => emit('update:valid', comment.trim() !== ''),
  { immediate: true }
)
</script>

<template>
  <div class="monitoring-custom-notification-form">
    <label class="monitoring-custom-notification-form__field">
      <span class="monitoring-custom-notification-form__label">
        {{ _t('Comment') }}<CmkLabelRequired :show="true" space="before" />
      </span>
      <CmkInput
        v-model="model.comment"
        field-size="large"
        :placeholder="_t('Enter your message here')"
        :external-errors="commentErrors"
      />
    </label>
    <CmkCheckbox
      v-model="model.forced"
      :label="
        _t(
          'Send regardless of restrictions, e.g. notification period or disabled notifications (forced)'
        )
      "
    />
    <CmkCheckbox
      v-model="model.broadcast"
      :label="
        targetKind === 'host'
          ? _t('Send to all contacts of the selected hosts (broadcast)')
          : _t('Send to all contacts of the selected services (broadcast)')
      "
    />
  </div>
</template>

<style scoped>
.monitoring-custom-notification-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
  padding: var(--spacing);
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
}

.monitoring-custom-notification-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-custom-notification-form__label {
  display: flex;
  align-items: center;
  gap: var(--dimension-2);
  font-weight: var(--font-weight-bold);
}
</style>
