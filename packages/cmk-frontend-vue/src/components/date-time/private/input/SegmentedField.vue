<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import GhostWidth from '../display/GhostWidth.vue'
import { type SegmentedFieldApi, selectInputOnFocus } from './useSegmentedField'

withDefaults(
  defineProps<{
    /** The engine driving this field — see `useSegmentedField`. */
    api: SegmentedFieldApi
    /** Disable the inputs. */
    disabled?: boolean
    /** Accessible name for the segment group; defaults to "Date and time". */
    ariaLabel?: TranslatedString
  }>(),
  {
    disabled: false
  }
)

const { _t } = usei18n()
</script>

<template>
  <span
    class="cmk-segmented-field"
    :class="{ 'cmk-segmented-field--disabled': disabled }"
    role="group"
    :aria-label="ariaLabel ?? _t('Date and time')"
    :aria-disabled="disabled || undefined"
    :aria-invalid="api.state.value === 'partial' || undefined"
    @focusout="api.onFieldFocusOut"
  >
    <template v-for="view in api.views.value" :key="view.key">
      <span v-if="view.separator" class="cmk-segmented-field__separator" aria-hidden="true">{{
        view.separator
      }}</span>
      <GhostWidth :variants="view.options">
        <input
          :ref="(el) => api.registerInput(view.key, el as HTMLInputElement | null)"
          class="cmk-segmented-field__segment"
          :class="{ 'cmk-segmented-field__segment--enum': !view.editable }"
          type="text"
          role="spinbutton"
          :inputmode="view.editable ? 'numeric' : 'text'"
          :readonly="!view.editable"
          :maxlength="view.maxlength"
          :size="view.maxlength"
          :style="{ minInlineSize: `${view.widthCh}ch` }"
          :value="view.text"
          :disabled="disabled"
          :aria-label="view.ariaLabel"
          :aria-valuenow="view.valueNow"
          :aria-valuemin="view.valueMin"
          :aria-valuemax="view.valueMax"
          :aria-valuetext="view.valueText"
          :placeholder="view.placeholder"
          @input="api.onInput(view.key, $event)"
          @keydown="api.onKey(view.key, $event)"
          @focus="selectInputOnFocus"
          @blur="api.onBlur"
        />
      </GhostWidth>
    </template>
  </span>
</template>

<style scoped>
.cmk-segmented-field {
  /* Local color hooks so the later coloring pass can re-point them per theme in one place. */
  --cmk-segmented-field-selection-bg: var(--color-corporate-green-50);
  --cmk-segmented-field-selection-fg: var(--color-conference-grey-100);

  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 0;
  font-variant-numeric: tabular-nums;
  color: var(--font-color);
}

.cmk-segmented-field--disabled {
  pointer-events: none;
}

.cmk-segmented-field__segment {
  flex: none;
  box-sizing: content-box;
  field-sizing: content;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: var(--dimension-2);
  background: transparent;
  color: var(--font-color);
  font-size: var(--font-size-normal);
  font-variant-numeric: tabular-nums;
  text-align: center;
  outline: none;
  box-shadow: none;

  &:focus {
    background: var(--cmk-segmented-field-selection-bg);
    color: var(--cmk-segmented-field-selection-fg);
  }

  &[readonly] {
    cursor: default;
    caret-color: transparent;
  }
}

/* Fill the ghost-reserved cell so the (centered) text stays put while cycling options. */
.cmk-segmented-field__segment--enum {
  inline-size: 100%;
}

.cmk-segmented-field__separator {
  color: var(--font-color);
}
</style>
