<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type VariantProps, cva } from 'class-variance-authority'
import { computed } from 'vue'

import useId from '@/lib/useId'

import useProgressLabel, { type ProgressLabel } from './useProgressLabel'

const sizes = cva('', {
  variants: {
    size: {
      small: 'cmk-progress-circle--small',
      medium: 'cmk-progress-circle--medium',
      large: 'cmk-progress-circle--large'
    }
  },
  defaultVariants: {
    size: 'medium'
  }
})

const colors = cva('', {
  variants: {
    color: {
      success: 'cmk-progress-circle--color-success',
      warning: 'cmk-progress-circle--color-warning',
      danger: 'cmk-progress-circle--color-danger',
      font: 'cmk-progress-circle--color-font'
    }
  },
  defaultVariants: {
    color: 'success'
  }
})

const fontColors = cva('', {
  variants: {
    fontColor: {
      success: 'cmk-progress-circle--font-color-success',
      warning: 'cmk-progress-circle--font-color-warning',
      danger: 'cmk-progress-circle--font-color-danger',
      font: 'cmk-progress-circle--font-color-font'
    }
  }
})

export type Sizes = VariantProps<typeof sizes>['size']
export type Colors = VariantProps<typeof colors>['color']
export type FontColors = VariantProps<typeof fontColors>['fontColor']

const SIZE_GEOMETRY: Record<NonNullable<Sizes>, { diameter: number; stroke: number }> = {
  small: { diameter: 36, stroke: 3 },
  medium: { diameter: 56, stroke: 4 },
  large: { diameter: 80, stroke: 6 }
}

export interface CmkProgressCircleDefaultProps {
  value?: number
  size?: Sizes
  color?: Colors
  fontColor?: FontColors
  max?: number | 'unknown'
  label?: ProgressLabel
  reverse?: boolean
}

const {
  value = 0,
  size = 'medium',
  color = 'success',
  fontColor = undefined,
  max = 100,
  label = undefined,
  reverse = false
} = defineProps<CmkProgressCircleDefaultProps>()

const { accessibilityLabelString, labelString, progressRatio } = useProgressLabel(() => ({
  value,
  max,
  label
}))

const geometry = computed(() => SIZE_GEOMETRY[size ?? 'medium'])
const radius = computed(() => (geometry.value.diameter - geometry.value.stroke) / 2)
const center = computed(() => geometry.value.diameter / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const dashOffset = computed(() =>
  reverse
    ? circumference.value * progressRatio.value
    : circumference.value * (1 - progressRatio.value)
)

const cmkProgressCircleId = useId()
</script>

<template>
  <div
    class="cmk-progress-circle"
    :class="[sizes({ size }), colors({ color }), fontColors({ fontColor })]"
    :title="accessibilityLabelString"
    role="progressbar"
    :aria-valuemax="max"
    :aria-valuemin="0"
    :aria-valuenow="value"
    :aria-labelledby="cmkProgressCircleId"
  >
    <svg
      class="cmk-progress-circle__svg"
      :class="{ 'cmk-progress-circle__svg--infinite': max === 'unknown' }"
      :width="geometry.diameter"
      :height="geometry.diameter"
      :viewBox="`0 0 ${geometry.diameter} ${geometry.diameter}`"
    >
      <circle
        class="cmk-progress-circle__track"
        :cx="center"
        :cy="center"
        :r="radius"
        :stroke-width="geometry.stroke"
        fill="none"
      />
      <circle
        class="cmk-progress-circle__indicator"
        :cx="center"
        :cy="center"
        :r="radius"
        :stroke-width="geometry.stroke"
        fill="none"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="max === 'unknown' ? circumference * 0.75 : dashOffset"
      />
    </svg>
    <label
      :id="cmkProgressCircleId"
      class="cmk-progress-circle__label"
      :class="{ 'cmk-progress-circle__label--visible': label && max !== 'unknown' }"
    >
      {{ labelString }}
    </label>
  </div>
</template>

<style scoped>
.cmk-progress-circle {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.cmk-progress-circle__svg {
  transform: rotate(-90deg);
}

.cmk-progress-circle__svg--infinite {
  animation: infinite-circle-progress 1.5s linear infinite;
}

.cmk-progress-circle__track {
  stroke: var(--ux-theme-6);
}

.cmk-progress-circle__indicator {
  stroke: var(--cmk-progress-circle-color);
  stroke-linecap: round;
  transition: stroke-dashoffset 660ms ease-in-out;
}

.cmk-progress-circle__label {
  position: absolute;
  text-align: center;
  z-index: +1;
  font-size: 8px;
  color: var(--cmk-progress-circle-font-color, var(--cmk-progress-circle-color));
  visibility: hidden;

  &.cmk-progress-circle__label--visible {
    visibility: visible;
  }
}

.cmk-progress-circle--color-success {
  --cmk-progress-circle-color: var(--success);
}

.cmk-progress-circle--color-warning {
  --cmk-progress-circle-color: var(--color-warning);
}

.cmk-progress-circle--color-danger {
  --cmk-progress-circle-color: var(--color-dark-red-40);
}

.cmk-progress-circle--color-font {
  --cmk-progress-circle-color: var(--font-color);
}

.cmk-progress-circle--font-color-success {
  --cmk-progress-circle-font-color: var(--success);
}

.cmk-progress-circle--font-color-warning {
  --cmk-progress-circle-font-color: var(--color-warning);
}

.cmk-progress-circle--font-color-danger {
  --cmk-progress-circle-font-color: var(--color-dark-red-40);
}

.cmk-progress-circle--font-color-font {
  --cmk-progress-circle-font-color: var(--font-color);
}

body[data-theme='facelift'] {
  .cmk-progress-circle--color-success {
    --cmk-progress-circle-color: var(--color-corporate-green-70);
  }

  .cmk-progress-circle--color-warning {
    --cmk-progress-circle-color: var(--color-yellow-70);
  }

  .cmk-progress-circle--color-danger {
    --cmk-progress-circle-color: var(--color-dark-red-50);
  }

  .cmk-progress-circle--font-color-success {
    --cmk-progress-circle-font-color: var(--color-corporate-green-70);
  }

  .cmk-progress-circle--font-color-warning {
    --cmk-progress-circle-font-color: var(--color-yellow-70);
  }

  .cmk-progress-circle--font-color-danger {
    --cmk-progress-circle-font-color: var(--color-dark-red-50);
  }
}

.cmk-progress-circle--small .cmk-progress-circle__label {
  font-size: 9px;
}

.cmk-progress-circle--medium .cmk-progress-circle__label {
  font-size: 11px;
}

.cmk-progress-circle--large .cmk-progress-circle__label {
  font-size: 14px;
}

@keyframes infinite-circle-progress {
  from {
    transform: rotate(-90deg);
  }

  to {
    transform: rotate(270deg);
  }
}
</style>
