<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { computed, useId } from 'vue'

const sizes = cva('', {
  variants: {
    size: {
      small: 'small',
      medium: 'medium',
      large: 'large'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

export type Sizes = VariantProps<typeof sizes>['size']

export interface CmkProgressbarDefaultProps {
  value?: number
  size?: Sizes
  max?: number | 'unknown'
  label?: { showTotal?: boolean; unit?: string } | boolean | undefined
}

const {
  value = 0,
  size = 'medium',
  max = 100,
  label = undefined
} = defineProps<CmkProgressbarDefaultProps>()

const accessibilityLabelString = computed<string>(() => {
  if (max === 'unknown' || typeof max === 'undefined') {
    return 'unknown progress'
  }

  if (label) {
    if (label !== true) {
      return `${value.toFixed(0)}${label?.showTotal ? ' / '.concat(max.toFixed(0)) : ''} ${label?.unit}`.trim()
    }
  }

  return value.toFixed(0)
})

const labelString = computed<string>(() => {
  if (label) {
    return accessibilityLabelString.value
  }

  return ''
})
const progressRatio = computed(() => (max === 'unknown' ? 0 : value / max))

const cmkProgressbaId = useId()
</script>

<template>
  <div
    :max="max"
    class="cmk-progressbar"
    :class="sizes({ size })"
    :title="accessibilityLabelString"
    role="progressbar"
    :aria-valuemax="max"
    :aria-valuemin="0"
    :aria-valuenow="value"
    :aria-labelledby="cmkProgressbaId"
  >
    <label
      :id="cmkProgressbaId"
      class="cmk-progress-label"
      :class="{ visible: label && max !== 'unknown' }"
    >
      {{ labelString }}
    </label>
    <div
      v-if="max !== 'unknown'"
      class="cmk-progressbar-indicator"
      :style="`transform: translateX(-${100 - progressRatio * 100}%)`"
    />
    <div v-if="max === 'unknown'" class="cmk-progressbar-indicator-infinite" />
  </div>
</template>

<style scoped>
.cmk-progressbar {
  position: relative;
  overflow: hidden;
  background: var(--ux-theme-1);
  border-radius: 99999px;
  width: 100%;
  height: 100%;
  transform: translateZ(0);
  display: flex;
  align-items: center;
}

.cmk-progressbar-indicator {
  background: var(--success);
  width: 100%;
  height: 100%;
  border-radius: 99999px;
  transition: transform 660ms ease-in-out;
}

.cmk-progressbar-indicator-infinite {
  background: var(--success);
  width: 50%;
  height: 100%;
  border-radius: 99999px;
  animation: infinite-progress 1.5s ease-in-out;
  animation-iteration-count: infinite;
}

@keyframes infinite-progress {
  from {
    transform: translateX(-201%);
  }
  to {
    transform: translateX(201%);
  }
}

.cmk-progress-label {
  width: 100%;
  text-align: center;
  position: absolute;
  z-index: +1;
  font-size: 8px;
  visibility: hidden;

  &.visible {
    visibility: visible;
  }
}

.small {
  height: 4px;

  &:has(.cmk-progress-label) {
    height: 8px;
  }
}

.medium {
  height: 8px;
}

.large {
  height: 12px;

  .cmk-progress-label {
    font-size: 10px;
  }
}
</style>
