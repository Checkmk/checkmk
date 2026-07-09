<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n, { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton'
import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

import type { DateTimeSaveSlots } from '../../types'

const props = withDefaults(
  defineProps<{
    /** Show the Save checkbox and its slotted content; the Apply button becomes "Save & apply". */
    saveMode?: boolean
    /** Label for the Save checkbox; defaults to "Save". */
    saveLabel?: TranslatedString | undefined
    /** Disable the Apply button (e.g. while the staged value is incomplete). */
    applyDisabled?: boolean
    /** Reason Apply is disabled. */
    applyDisabledReason?: TranslatedString | undefined
    /** Announces to screen readers that the save is in progress. */
    pendingSave?: boolean
    /** Stretch the Apply/Cancel buttons across the footer (for narrow popups). */
    stretchActions?: boolean
  }>(),
  {
    saveMode: false,
    applyDisabled: false,
    pendingSave: false,
    stretchActions: false
  }
)

/** Whether the Save checkbox is ticked (only meaningful in save mode). */
const saveChecked = defineModel<boolean>('saveChecked', { default: false })

const emit = defineEmits<{
  /** The user pressed Apply. */
  (e: 'apply'): void
  /** The user pressed Cancel. */
  (e: 'cancel'): void
}>()

defineSlots<DateTimeSaveSlots>()

const { _t } = usei18n()

const applyLabel = computed<TranslatedString>(() =>
  props.saveMode && saveChecked.value ? _t('Save & apply') : _t('Apply')
)

const applyStatus = computed<TranslatedString>(() =>
  props.pendingSave
    ? _t('Saving…')
    : props.applyDisabled && props.applyDisabledReason !== undefined
      ? props.applyDisabledReason
      : untranslated('')
)
</script>

<template>
  <div
    class="cmk-date-time-flyout-footer"
    :class="{
      'cmk-date-time-flyout-footer--stretch-actions': stretchActions,
      'cmk-date-time-flyout-footer--save-open': saveMode && saveChecked
    }"
  >
    <div v-if="saveMode" class="cmk-date-time-flyout-footer__save">
      <div class="cmk-date-time-flyout-footer__save-toggle">
        <CmkCheckbox v-model="saveChecked" :label="saveLabel ?? _t('Save')" :padding="'both'" />
      </div>
      <div v-if="saveChecked" class="cmk-date-time-flyout-footer__save-content">
        <slot name="save" />
      </div>
    </div>
    <div class="cmk-date-time-flyout-footer__actions">
      <CmkButton
        class="cmk-date-time-flyout-footer__action"
        variant="primary"
        :disabled="applyDisabled"
        @click="emit('apply')"
      >
        {{ applyLabel }}
      </CmkButton>
      <CmkVisuallyHidden :text="applyStatus" live="polite" />
      <CmkButton
        class="cmk-date-time-flyout-footer__action"
        variant="optional"
        @click="emit('cancel')"
      >
        {{ _t('Cancel') }}
      </CmkButton>
    </div>
  </div>
</template>

<style scoped>
.cmk-date-time-flyout-footer {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-5);
  border-top: 1px solid
    var(--cmk-flyout-popup-border-color, var(--default-form-element-border-color));
  padding: var(--cmk-dt-flyout-footer-padding, var(--dimension-7));
}

.cmk-date-time-flyout-footer__save {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

/* Match the button height so the checkbox label lines up with the Apply/Cancel labels. */
.cmk-date-time-flyout-footer__save-toggle {
  display: flex;
  align-items: center;
  min-height: var(--dimension-10);
}

.cmk-date-time-flyout-footer__actions {
  display: flex;
  gap: var(--dimension-4);
  margin-left: auto;
}

.cmk-date-time-flyout-footer--save-open .cmk-date-time-flyout-footer__actions {
  align-self: flex-end;
}

.cmk-date-time-flyout-footer--stretch-actions .cmk-date-time-flyout-footer__actions {
  flex: 1 1 0;
}

.cmk-date-time-flyout-footer--stretch-actions .cmk-date-time-flyout-footer__action {
  flex: 1 1 0;
  justify-content: center;
}
</style>
