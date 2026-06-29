<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkInput from '@/components/user-input/CmkInput.vue'

import type { CommentActionValues } from './types'

const model = defineModel<CommentActionValues>({ required: true })

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
  <label class="monitoring-action-comment-form">
    <span class="monitoring-action-comment-form__label">{{ _t('Comment') }}</span>
    <CmkInput v-model="model.comment" field-size="large" :placeholder="_t('Enter a comment…')" />
  </label>
</template>

<style scoped>
.monitoring-action-comment-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.monitoring-action-comment-form__label {
  font-weight: var(--font-weight-bold);
}
</style>
