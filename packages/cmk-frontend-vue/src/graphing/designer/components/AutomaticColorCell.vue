<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useId } from 'vue'

import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'

const { _t } = usei18n()

const id = useId()
const message = _t('Colors are assigned automatically to multi-metric queries.')
</script>

<template>
  <BaseCell column-id="color" vertical-align="middle">
    <svg
      class="graphing-automatic-color-cell__wheel"
      role="img"
      viewBox="0 0 12 12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{{ message }}</title>
      <g :clip-path="`url(#${id}-clip)`">
        <g :filter="`url(#${id}-tiles)`">
          <path d="M-6 -6H4V4H-6V-6Z" fill="#FFD703" />
          <path d="M4 -6H8V4H4V-6Z" fill="#FF9D33" />
          <path d="M8 -6H18V4H8V-6Z" fill="#C43131" />
          <path d="M-6 4H4V8H-6V4Z" fill="#EC48B6" />
          <path d="M4 4H8V8H4V4Z" fill="#8380FF" />
          <path d="M8 4H18V8H8V4Z" fill="#28A2F3" />
          <path d="M-6 8H4V18H-6V8Z" fill="#0667C1" />
          <path d="M4 8H8V18H4V8Z" fill="#1EE6E6" />
          <path d="M8 8H18V18H8V8Z" fill="#15D1A0" />
        </g>
        <g :filter="`url(#${id}-spark)`">
          <path
            d="M7.51503 9.95044C11.6522 8.10843 14.0592 4.48835 12.8911 1.86476C11.723 -0.758833 7.42218 -1.39244 3.28497 0.449565C-0.852233 2.29157 -3.25917 5.91165 -2.09107 8.53524C-0.922971 11.1588 3.37783 11.7924 7.51503 9.95044Z"
            :fill="`url(#${id}-spark-outer)`"
          />
          <path
            opacity="0.55"
            d="M2.10675 9.07922C4.02166 10.5753 6.51118 10.5886 7.66725 9.1089C8.82332 7.6292 8.20816 5.21684 6.29325 3.72075C4.37834 2.22466 1.88882 2.21138 0.732755 3.69108C-0.423315 5.17078 0.191845 7.58313 2.10675 9.07922Z"
            :fill="`url(#${id}-spark-inner)`"
          />
        </g>
      </g>
      <defs>
        <filter :id="`${id}-tiles`" color-interpolation-filters="sRGB">
          <feGaussianBlur stdDeviation="1.25" />
        </filter>
        <filter :id="`${id}-spark`" color-interpolation-filters="sRGB">
          <feGaussianBlur stdDeviation="0.5" />
        </filter>
        <radialGradient
          :id="`${id}-spark-outer`"
          cx="0"
          cy="0"
          r="1"
          gradientUnits="userSpaceOnUse"
          gradientTransform="translate(5.4 5.2) rotate(-24) scale(8.2 5.2)"
        >
          <stop stop-color="white" />
          <stop offset="0.38" stop-color="white" stop-opacity="0.6" />
          <stop offset="0.72" stop-color="white" stop-opacity="0.22" />
          <stop offset="1" stop-color="white" stop-opacity="0" />
        </radialGradient>
        <radialGradient
          :id="`${id}-spark-inner`"
          cx="0"
          cy="0"
          r="1"
          gradientUnits="userSpaceOnUse"
          gradientTransform="translate(4.2 6.39999) rotate(38) scale(4.4 3.4)"
        >
          <stop stop-color="white" />
          <stop offset="0.38" stop-color="white" stop-opacity="0.6" />
          <stop offset="0.72" stop-color="white" stop-opacity="0.22" />
          <stop offset="1" stop-color="white" stop-opacity="0" />
        </radialGradient>
        <clipPath :id="`${id}-clip`">
          <rect width="12" height="12" rx="1" />
        </clipPath>
      </defs>
    </svg>
  </BaseCell>
</template>

<style scoped>
.graphing-automatic-color-cell__wheel {
  display: block;
  width: var(--dimension-5);
  height: var(--dimension-5);
}
</style>
