<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Component, computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'

import ActionCommentForm from './ActionCommentForm.vue'
import { type ActionFormDefinition, type ActionFormValues, defaultActionValues } from './types'

const ACTION_FORM_COMPONENTS: Partial<Record<ActionFormDefinition['type'], Component>> = {
  comment: ActionCommentForm
}

const props = defineProps<{
  definition: ActionFormDefinition
  title: TranslatedString
  subtitle?: TranslatedString | undefined
  submitLabel?: TranslatedString | undefined
}>()

const emit = defineEmits<{
  (event: 'submit', values: ActionFormValues): void
  (event: 'cancel'): void
}>()

const { _t } = usei18n()

const draft = ref<ActionFormValues>(defaultActionValues(props.definition))
const isValid = ref(props.definition.type === 'confirm')

const formComponent = computed<Component | undefined>(
  () => ACTION_FORM_COMPONENTS[props.definition.type]
)

watch(
  () => props.definition,
  (definition) => {
    draft.value = defaultActionValues(definition)
    isValid.value = definition.type === 'confirm'
  }
)

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
    <header class="monitoring-action-form-pane__header">
      <h2 class="monitoring-action-form-pane__title">{{ title }}</h2>
      <p v-if="subtitle" class="monitoring-action-form-pane__subtitle">{{ subtitle }}</p>
    </header>

    <div class="monitoring-action-form-pane__body">
      <component
        :is="formComponent"
        v-if="formComponent"
        v-model="draft"
        :definition="definition"
        @update:valid="isValid = $event"
      />
      <p v-else class="monitoring-action-form-pane__confirm">
        {{ _t('This action runs immediately and has no further options.') }}
      </p>
    </div>

    <div class="monitoring-action-form-pane__footer">
      <CmkButton variant="primary" size="small" :disabled="!isValid" @click="submit">
        {{ submitLabel ?? _t('Apply') }}
      </CmkButton>
      <CmkButton size="small" @click="cancel">{{ _t('Cancel') }}</CmkButton>
    </div>
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

.monitoring-action-form-pane__footer {
  display: flex;
  flex: 0 0 auto;
  gap: var(--dimension-4);
  align-items: center;
  padding-top: var(--dimension-4);
  border-top: 1px solid var(--ux-theme-4);
}
</style>
