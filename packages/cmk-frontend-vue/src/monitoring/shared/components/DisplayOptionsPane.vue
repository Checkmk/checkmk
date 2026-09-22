<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { DEFAULT_DISPLAY_OPTIONS, type DisplayOptions } from '@/monitoring/shared/types'

const props = defineProps<{
  modelValue: DisplayOptions
}>()

const emit = defineEmits<{
  (event: 'submit', value: DisplayOptions): void
  (event: 'cancel'): void
}>()

const { _t } = usei18n()

const draft = ref<DisplayOptions>({ ...props.modelValue })

const dateFormatOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: '%Y-%m-%d', title: untranslated('1970-12-18') },
    { name: '%d.%m.%Y', title: untranslated('18.12.1970') },
    { name: '%m/%d/%Y', title: untranslated('12/18/1970') },
    { name: '%d.%m.', title: untranslated('18.12.') },
    { name: '%m/%d', title: untranslated('12/18') }
  ]
}

const timestampFormatOptions: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'mixed', title: _t('Mixed') },
    { name: 'abs', title: _t('Absolute') },
    { name: 'rel', title: _t('Relative') },
    { name: 'both', title: _t('Both') },
    { name: 'epoch', title: _t('Unix timestamp (epoch)') }
  ]
}

const dateFormat = computed<string | null>({
  get: () => draft.value.dateFormat,
  set: (value) => {
    if (value !== null) {
      draft.value = { ...draft.value, dateFormat: value as DisplayOptions['dateFormat'] }
    }
  }
})

const timestampFormat = computed<string | null>({
  get: () => draft.value.timestampFormat,
  set: (value) => {
    if (value !== null) {
      draft.value = { ...draft.value, timestampFormat: value as DisplayOptions['timestampFormat'] }
    }
  }
})

function submit(): void {
  emit('submit', draft.value)
}

function reset(): void {
  draft.value = { ...DEFAULT_DISPLAY_OPTIONS }
}

function cancel(): void {
  emit('cancel')
}
</script>

<template>
  <div class="monitoring-display-options-pane">
    <header class="monitoring-display-options-pane__header">
      <h2 class="monitoring-display-options-pane__title">{{ _t('Modify display options') }}</h2>
      <CmkIconButton
        class="monitoring-display-options-pane__close"
        name="close"
        size="xsmall"
        :title="_t('Close')"
        :aria-label="_t('Close')"
        @click="cancel"
      />
    </header>

    <div class="monitoring-display-options-pane__actions">
      <CmkButton variant="primary" size="medium" @click="submit">{{ _t('Submit') }}</CmkButton>
      <CmkButton variant="optional" size="medium" @click="reset">{{ _t('Reset') }}</CmkButton>
    </div>

    <div class="monitoring-display-options-pane__body">
      <div class="monitoring-display-options-pane__field">
        <span class="monitoring-display-options-pane__label">{{ _t('Date format') }}</span>
        <CmkDropdown v-model="dateFormat" :options="dateFormatOptions" :label="_t('Date format')" />
      </div>
      <div class="monitoring-display-options-pane__field">
        <span class="monitoring-display-options-pane__label">{{ _t('Timestamp format') }}</span>
        <CmkDropdown
          v-model="timestampFormat"
          :options="timestampFormatOptions"
          :label="_t('Timestamp format')"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.monitoring-display-options-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  padding: var(--spacing);
  gap: var(--spacing);
}

.monitoring-display-options-pane__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--dimension-3);
}

.monitoring-display-options-pane__title {
  margin: 0;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);
}

.monitoring-display-options-pane__close {
  margin-left: auto;
}

.monitoring-display-options-pane__actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--dimension-4);
  align-items: center;
}

.monitoring-display-options-pane__body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--spacing);
  min-height: 0;
  overflow: auto;
}

.monitoring-display-options-pane__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.monitoring-display-options-pane__label {
  color: var(--font-color-dimmed);
}
</style>
