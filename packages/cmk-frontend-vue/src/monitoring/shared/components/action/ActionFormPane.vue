<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Component, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIndent from '@/components/CmkIndent.vue'

const props = defineProps<{
  title: TranslatedString
  subtitle?: TranslatedString | undefined
  submitLabel?: TranslatedString | undefined
  form?: Component | undefined
  initialValues?: unknown
  indent?: boolean | undefined
}>()

const emit = defineEmits<{
  (event: 'submit', values: unknown): void
  (event: 'cancel'): void
}>()

const { _t } = usei18n()

const draft = ref(props.initialValues)
const isValid = ref(props.form === undefined)

function submit(): void {
  if (!isValid.value) {
    return
  }
  emit('submit', draft.value)
}

function cancel(): void {
  emit('cancel')
}
</script>

<template>
  <div class="monitoring-action-form-pane">
    <component :is="indent ? CmkIndent : 'div'" class="monitoring-action-form-pane__group">
      <header class="monitoring-action-form-pane__header">
        <div class="monitoring-action-form-pane__title-row">
          <h2 class="monitoring-action-form-pane__title">{{ title }}</h2>
        </div>
        <p v-if="subtitle" class="monitoring-action-form-pane__subtitle">{{ subtitle }}</p>
      </header>

      <div class="monitoring-action-form-pane__actions">
        <CmkButton variant="primary" size="medium" :disabled="!isValid" @click="submit">
          {{ submitLabel ?? _t('Apply') }}
        </CmkButton>
        <CmkButton size="medium" @click="cancel">{{ _t('Cancel') }}</CmkButton>
      </div>

      <div class="monitoring-action-form-pane__body">
        <component :is="form" v-if="form" v-model="draft" @update:valid="isValid = $event" />
        <p v-else class="monitoring-action-form-pane__confirm">
          {{ _t('This action runs immediately and has no further options.') }}
        </p>
      </div>
    </component>
  </div>
</template>

<style scoped>
.monitoring-action-form-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  padding: var(--spacing);
  gap: var(--spacing);
}

.monitoring-action-form-pane__header {
  flex: 0 0 auto;
}

.monitoring-action-form-pane__title-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.monitoring-action-form-pane__title {
  margin: 0;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
}

.monitoring-action-form-pane__subtitle {
  margin: var(--dimension-2) 0 0;
  color: var(--font-color-dimmed);
}

.monitoring-action-form-pane__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.monitoring-action-form-pane__confirm {
  margin: 0;
  color: var(--font-color-dimmed);
}

.monitoring-action-form-pane__group {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--spacing);
  min-height: 0;
}

.monitoring-action-form-pane__actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--dimension-4);
  align-items: center;
}
</style>
