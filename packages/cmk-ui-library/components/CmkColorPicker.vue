<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { contrastTextColor } from 'cmk-ui-library/lib/contrastText'
import { computed, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })

export type Sizes = 'small' | 'large'

export interface CmkColorPickerProps {
  size?: Sizes
}

const { size = 'large' } = defineProps<CmkColorPickerProps>()

const slots = defineSlots<{
  default?(props: { contrastColor: string }): unknown
}>()

const modelValue = defineModel({ type: String, default: '#ff0000' })

const contrast = computed(() => contrastTextColor(modelValue.value))

const attrs = useAttrs()
const rootAttrs = computed(() => ({ class: attrs['class'], style: attrs['style'] }))
const inputAttrs = computed(() =>
  Object.fromEntries(Object.entries(attrs).filter(([name]) => name !== 'class' && name !== 'style'))
)
</script>

<template>
  <span
    class="cmk-color-picker"
    :class="{ 'cmk-color-picker--small': size === 'small' }"
    v-bind="rootAttrs"
  >
    <input v-model="modelValue" v-bind="inputAttrs" class="cmk-color-picker__input" type="color" />
    <span
      v-if="slots.default"
      class="cmk-color-picker__content"
      aria-hidden="true"
      :style="{ color: contrast }"
    >
      <slot :contrast-color="contrast" />
    </span>
    <span class="cmk-color-picker__triangle" :style="{ backgroundColor: contrast }" />
  </span>
</template>

<style scoped>
.cmk-color-picker {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-width: var(--cmk-color-picker-size);
  height: var(--cmk-color-picker-size);

  --cmk-color-picker-border: var(--color-mid-grey-50);
  --cmk-color-picker-bg: var(--color-daylight-grey-60);
  --cmk-color-picker-size: var(--dimension-10);
  --cmk-color-picker-padding: var(--dimension-3);
  --cmk-color-picker-triangle-inset: 7.5px;
}

body[data-theme='modern-dark'] .cmk-color-picker {
  --cmk-color-picker-border: var(--color-mid-grey-60);
  --cmk-color-picker-bg: var(--color-midnight-grey-100);
}

.cmk-color-picker--small {
  --cmk-color-picker-size: var(--dimension-7);
  --cmk-color-picker-padding: 3px;
  --cmk-color-picker-triangle-inset: 6px;
}

.cmk-color-picker__input {
  position: absolute;
  inset: 0;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  padding: var(--cmk-color-picker-padding);
  margin: 0;
  border: 1px solid var(--cmk-color-picker-border);
  border-radius: var(--border-radius);
  background: var(--cmk-color-picker-bg);
  cursor: pointer;

  &:focus-visible {
    outline: revert;
  }

  &:hover {
    background: color-mix(in srgb, var(--cmk-color-picker-bg) 90%, var(--color-white-100) 10%);
  }
}

.cmk-color-picker__input::-webkit-color-swatch-wrapper {
  padding: 0;
}

.cmk-color-picker__input::-webkit-color-swatch {
  border: none;
  border-radius: var(--border-radius);
}

.cmk-color-picker__input::-moz-color-swatch {
  border: none;
  border-radius: var(--border-radius);
}

.cmk-color-picker__content {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 calc((var(--cmk-color-picker-size) - 1em) / 2);
  font-size: var(--font-size-normal);
  font-weight: var(--font-weight-bold);
  line-height: 1;
  pointer-events: none;
}

.cmk-color-picker__triangle {
  position: absolute;
  right: var(--cmk-color-picker-triangle-inset);
  bottom: var(--cmk-color-picker-triangle-inset);
  width: 5px;
  height: 5px;
  clip-path: polygon(100% 100%, 0 100%, 100% 0);
  pointer-events: none;
}
</style>
