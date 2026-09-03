<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A colour beside the hex code it stands for, and optionally a switch that turns
the colour off altogether — "off" stores the sentinel the caller names, which is
how a map object says "inherit" or "transparent" rather than "some colour".
-->
<script setup lang="ts">
import CmkColorPicker from 'cmk-ui-library/components/CmkColorPicker.vue'
import CmkSwitch from 'cmk-ui-library/components/CmkSwitch.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string | null | undefined
  /** Renders the on/off switch when set; without it the picker is always live. */
  enableLabel?: TranslatedString
  defaultColor: string
  /** What "off" stores — null (default) or a keyword such as 'transparent'. */
  noneValue?: string | null
}>()

const emit = defineEmits<{ 'update:modelValue': [string | null] }>()

const { _t } = usei18n()

// The native colour popup outlives an input that unmounts while it is open,
// leaving a picker floating over an unrelated view.
const rootEl = ref<HTMLElement | null>(null)
onBeforeUnmount(() => {
  rootEl.value?.querySelector<HTMLInputElement>('input[type="color"]')?.blur()
})

const enabled = computed(() => {
  if (props.enableLabel === undefined) {
    return true
  }
  const value = props.modelValue
  if (value === null || value === undefined || value === '') {
    return false
  }
  const none = props.noneValue ?? null
  return none === null ? true : value !== none
})

const displayedColor = computed(() => {
  const value = props.modelValue
  return value !== null && value !== undefined && value !== '' ? value : props.defaultColor
})

const HEX_PATTERN = /^#[0-9a-fA-F]{6}$/

const hexValidators = computed(() =>
  enabled.value
    ? [
        (value: string) => {
          const typed = (value ?? '').trim()
          if (!typed || typed === (props.noneValue ?? '')) {
            return []
          }
          return HEX_PATTERN.test(typed)
            ? []
            : [_t("Use a 6-digit hex code like '#ffffff' or 'transparent'")]
        }
      ]
    : []
)

function setEnabled(checked: boolean) {
  emit('update:modelValue', checked ? props.defaultColor : (props.noneValue ?? null))
}

function setColor(color: string) {
  if (enabled.value) {
    emit('update:modelValue', color)
  }
}

/**
 * What the hex field shows. It follows the stored colour, but is not the same
 * thing: a value is only a colour once it is typed out, and until then it lives
 * here alone.
 */
const typed = ref('')
watch(
  () => (enabled.value ? displayedColor.value : ''),
  (value) => {
    typed.value = value
  },
  { immediate: true }
)

/**
 * Commit what was typed, once it is a colour. `#ff` is not one, and handing it
 * to the form would both repaint the object from it and — since a value that is
 * no colour counts as "off" — disable the very field being typed in.
 *
 * An emptied field means "no colour", but only where there is no switch to say
 * so: with one, the switch owns off and an empty field is an edit in progress.
 */
function onTyped(value: string): void {
  typed.value = value
  const trimmed = value.trim()
  if (!trimmed) {
    if (props.enableLabel === undefined) {
      emit('update:modelValue', props.noneValue ?? null)
    }
    return
  }
  if (HEX_PATTERN.test(trimmed) || trimmed === props.noneValue) {
    setColor(trimmed)
  }
}
</script>

<template>
  <div ref="rootEl" class="maps-color-input">
    <!-- .stop on the switch: the slider toggles itself, and the wrapping label
         would forward a second click to the hidden checkbox. -->
    <label v-if="enableLabel !== undefined" class="maps-color-input__toggle">
      <CmkSwitch :model-value="enabled" @update:model-value="setEnabled" @click.stop />
      <span>{{ enableLabel }}</span>
    </label>
    <span
      class="maps-color-input__swatch"
      :class="{ 'maps-color-input__swatch--disabled': !enabled }"
    >
      <CmkColorPicker
        :model-value="displayedColor"
        :disabled="!enabled"
        @update:model-value="setColor"
      />
    </span>
    <CmkInput
      :model-value="typed"
      :placeholder="defaultColor"
      field-size="fill"
      class="maps-color-input__field"
      :disabled="!enabled"
      :validators="hexValidators"
      @update:model-value="onTyped(($event ?? '') as string)"
    />
  </div>
</template>

<style scoped>
.maps-color-input {
  display: flex;
  flex: 1;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-color-input__toggle {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  font-size: var(--font-size-normal);
  color: var(--font-color);
  cursor: pointer;
}

.maps-color-input__swatch {
  display: inline-flex;
  align-items: stretch;
}

.maps-color-input__swatch--disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.maps-color-input__field {
  flex: 1;
}
</style>
