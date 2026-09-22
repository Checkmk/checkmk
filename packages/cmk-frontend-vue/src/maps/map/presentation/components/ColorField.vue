<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

const { _t } = usei18n()

const props = defineProps<{
  label: TranslatedString
  value: string | null | undefined
  /** Effective colour applied when no explicit value is set. Resolved from the
      active presentation theme; omit (or pass 'transparent') for properties
      that default to no colour. */
  defaultColor?: string
}>()
const emit = defineEmits<{ set: [string | null] }>()

const HEX_RE = /^#[0-9a-fA-F]{6}$/

const effective = computed(() => props.value || props.defaultColor || '')
const showsCheckerboard = computed(
  () => !props.value && (!props.defaultColor || props.defaultColor === 'transparent')
)
const swatchStyle = computed(() =>
  showsCheckerboard.value ? undefined : { backgroundColor: effective.value }
)
const pickerValue = computed(() => (HEX_RE.test(effective.value) ? effective.value : '#3b82f6'))
const title = computed(() =>
  props.value ? `${props.label}: ${props.value}` : `${props.label}: ${_t('theme default')}`
)

// On change rather than on input: the native picker fires continuously while
// the wheel is dragged, and every emit is one undo step and one save.
function onChange(e: Event): void {
  emit('set', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <label class="maps-color-field" :title="title">
    <!-- When unset the swatch previews the effective theme colour with a dashed
         border ("inherited"); the picker opens on that colour too. A theme whose
         default is transparent (e.g. text background) shows a checkerboard. -->
    <span
      class="maps-color-field__swatch"
      :class="{
        'maps-color-field__swatch--auto': !value,
        'maps-color-field__swatch--empty': showsCheckerboard
      }"
      :style="swatchStyle"
    >
      <input type="color" class="maps-color-field__input" :value="pickerValue" @change="onChange" />
    </span>
    <!-- Clearing to null returns the element to the theme default. -->
    <button
      v-if="value"
      class="maps-color-field__clear"
      :title="_t('Use theme color')"
      @click.prevent="emit('set', null)"
    >
      {{ untranslated('×') }}
    </button>
  </label>
</template>

<style scoped>
.maps-color-field {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.maps-color-field__swatch {
  position: relative;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  border: 1px solid var(--default-border-color, rgb(255 255 255 / 20%));
  overflow: hidden;
  cursor: pointer;
}

/* Unset: the colour is inherited from the theme — dashed border signals "auto". */
.maps-color-field__swatch--auto {
  border-style: dashed;
  border-color: var(--font-color-dimmed);
}

/* Transparent default: standard checkerboard so "no colour" reads clearly. */
.maps-color-field__swatch--empty {
  background-image:
    linear-gradient(45deg, rgb(255 255 255 / 12%) 25%, transparent 25%),
    linear-gradient(-45deg, rgb(255 255 255 / 12%) 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, rgb(255 255 255 / 12%) 75%),
    linear-gradient(-45deg, transparent 75%, rgb(255 255 255 / 12%) 75%);
  background-size: 10px 10px;
  background-position:
    0 0,
    0 5px,
    5px -5px,
    -5px 0;
}

.maps-color-field__input {
  position: absolute;
  inset: -4px;
  width: 40px;
  height: 40px;
  border: none;
  padding: 0;
  cursor: pointer;
  opacity: 0;
}

.maps-color-field__clear {
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: var(--font-color-dimmed);
  cursor: pointer;
  line-height: 1;
}
</style>
