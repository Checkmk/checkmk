<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{ variant: 'add' | 'remove' }>()

const emit = defineEmits<{ action: [] }>()

const { _t } = usei18n()
const addPinLabel = _t('Add pin')
const removePinLabel = _t('Remove pin')

const MINUS_BAR =
  'M9.62421 5.00757C10.1765 5.00757 10.624 5.45523 10.6241 6.00746C10.6238 6.55948 ' +
  '10.1763 7.00735 9.62421 7.00735H2.39017C1.83808 7.00735 1.3906 6.55948 1.39028 6.00746' +
  'C1.39034 5.45523 1.83792 5.00757 2.39017 5.00757L9.62421 5.00757Z'

function onClick(): void {
  emit('action')
}
</script>

<template>
  <button
    type="button"
    class="graphing-pin-handle"
    :aria-label="variant === 'add' ? addPinLabel : removePinLabel"
    @click.stop="onClick"
    @mousedown.stop
  >
    <svg class="graphing-pin-handle__svg" viewBox="0 0 20 20" aria-hidden="true">
      <circle class="graphing-pin-handle__halo" cx="10" cy="10" r="14" />
      <circle class="graphing-pin-handle__body" cx="10" cy="10" r="9.5" />
      <g transform="translate(4 4)">
        <circle class="graphing-pin-handle__disc" cx="6" cy="6" r="6" />
        <path class="graphing-pin-handle__glyph" :d="MINUS_BAR" />
        <path
          v-if="variant === 'add'"
          class="graphing-pin-handle__glyph"
          :d="MINUS_BAR"
          transform="rotate(90 6 6)"
        />
      </g>
    </svg>
  </button>
</template>

<style scoped>
.graphing-pin-handle {
  --graph-pin-body: var(--color-conference-grey-100, #1e262e);
  --graph-pin-outline: var(--color-white-100, #fff);
  --graph-pin-disc: var(--color-corporate-green-50, #15d1a0);
  --graph-pin-glyph: var(--color-conference-grey-100, #1e262e);

  position: absolute;
  z-index: 3;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  transform: translate(-50%, -100%);
}

.graphing-pin-handle__svg {
  display: block;
  width: 20px;
  height: auto;
  overflow: visible;
}

.graphing-pin-handle__halo {
  fill: none;
  stroke: var(--color-white-10, rgb(255 255 255 / 10%));
  stroke-width: 8px;
  opacity: 0;
}

.graphing-pin-handle:hover .graphing-pin-handle__halo {
  opacity: 1;
}

.graphing-pin-handle__body {
  fill: var(--graph-pin-body);
  stroke: var(--graph-pin-outline);
  stroke-width: 1;
}

.graphing-pin-handle__disc {
  fill: var(--graph-pin-disc);
}

.graphing-pin-handle__glyph {
  fill: var(--graph-pin-glyph);
}
</style>
