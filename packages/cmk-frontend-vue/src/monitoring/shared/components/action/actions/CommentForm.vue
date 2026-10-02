<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script lang="ts">
export interface CommentValues {
  comment: string
}

function hasComment(values: CommentValues): boolean {
  return values.comment.trim() !== ''
}
</script>

<script setup lang="ts">
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Whether to point out the fields that keep the form from being submitted. */
    showErrors?: boolean
  }>(),
  { showErrors: false }
)

const model = defineModel<CommentValues>({ required: true })

const emit = defineEmits<{
  (event: 'update:valid', valid: boolean): void
}>()

const { _t } = usei18n()

const commentErrors = computed(() =>
  props.showErrors && !hasComment(model.value) ? [_t('Comment is required.')] : []
)

watch(model, (values) => emit('update:valid', hasComment(values)), {
  immediate: true,
  deep: true
})
</script>

<template>
  <label class="monitoring-comment-form">
    <span class="monitoring-comment-form__label"
      >{{ _t('Comment') }}<CmkLabelRequired :show="true" space="before"
    /></span>
    <CmkInput
      v-model="model.comment"
      field-size="large"
      :placeholder="_t('Enter a comment…')"
      :external-errors="commentErrors"
    />
  </label>
</template>

<style scoped>
.monitoring-comment-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-comment-form__label {
  font-weight: var(--font-weight-bold);
}
</style>
