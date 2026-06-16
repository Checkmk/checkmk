<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'

import useId from '@/lib/useId'

import useProgressLabel, { type ProgressLabel } from './useProgressLabel'

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
  label?: ProgressLabel
}

const {
  value = 0,
  size = 'medium',
  max = 100,
  label = undefined
} = defineProps<CmkProgressbarDefaultProps>()

const { accessibilityLabelString, labelString, progressRatio } = useProgressLabel(() => ({
  value,
  max,
  label
}))

const cmkProgressbarId = useId()
</script>

<template>
  <div
    class="cmk-progressbar"
    :class="sizes({ size })"
    :title="accessibilityLabelString"
    role="progressbar"
    :aria-valuemax="max"
    :aria-valuemin="0"
    :aria-valuenow="value"
    :aria-labelledby="cmkProgressbarId"
  >
    <label
      :id="cmkProgressbarId"
      class="cmk-progress-label"
      :class="{ visible: label && max !== 'unknown' }"
    >
      {{ labelString }}
    </label>
    <div
      v-if="max !== 'unknown'"
      class="cmk-progressbar__indicator"
      :style="`transform: translateX(-${100 - progressRatio * 100}%)`"
    />
    <div v-if="max === 'unknown'" class="cmk-progressbar__indicator--infinite" />
  </div>
</template>

<style scoped>
.cmk-progressbar {
  position: relative;
  overflow: hidden;
  background: var(--ux-theme-6);
  border-radius: 99999px;
  width: 100%;
  height: 100%;
  transform: translateZ(0);
  display: flex;
  align-items: center;
}

.cmk-progressbar__indicator {
  background: var(--success);
  width: 100%;
  height: 100%;
  border-radius: 99999px;
  transition: transform 660ms ease-in-out;
}

.cmk-progressbar__indicator--infinite {
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

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-progress-label {
  width: 100%;
  text-align: center;
  position: absolute;
  z-index: +1;
  font-size: 8px;
  visibility: hidden;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &.visible {
    visibility: visible;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.small {
  height: 4px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  &:has(.cmk-progress-label.visible) {
    height: 8px;
  }
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.medium {
  height: 8px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.large {
  height: 12px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-progress-label {
    font-size: 10px;
  }
}
</style>
