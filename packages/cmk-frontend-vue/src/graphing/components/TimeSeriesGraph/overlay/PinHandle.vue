<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useId } from 'vue'

defineProps<{ variant: 'add' | 'remove' }>()

const emit = defineEmits<{ action: [] }>()

const { _t } = usei18n()
const addPinLabel = _t('Add pin')
const removePinLabel = _t('Remove pin')

// The design's marker, verbatim; colours are left to the stylesheet so the state can set them.
const BODY =
  'M4.5 0a4.5 4.5 0 0 1 3.897 6.75L5.414 13.45c-.353.79-1.475.79-1.827 0L.604 6.75A4.5 ' +
  '4.5 0 0 1 4.5 0m-.052 1.969a2.813 2.813 0 1 0 0 5.625 2.813 2.813 0 0 0 0-5.625'

const SILHOUETTE =
  'M4.5 0a4.5 4.5 0 0 1 3.897 6.75L5.414 13.45c-.353.79-1.475.79-1.827 0L.604 6.75A4.5 ' +
  '4.5 0 0 1 4.5 0'

// A stroke expanded into a fill, masked to the silhouette's inner half.
const OUTLINE =
  'M4.5 0v-1zM.604 6.75l.913-.407-.021-.048-.027-.046zm7.793 0-.913-.406zm0 ' +
  '0-.866-.501zM4.5 0v1A3.5 3.5 0 0 1 8 4.5h2A5.5 5.5 0 0 0 4.5-1zM9 4.5H8c0 .638-.171 ' +
  '1.234-.469 1.749l.866.5.865.501A5.5 5.5 0 0 0 10 4.5zm-.603 2.25-.913-.406L4.5 ' +
  '13.042l.914.407.913.407 2.984-6.699zm-4.81 ' +
  '6.699.913-.407-2.983-6.699-.913.407-.914.407 2.983 6.699zM.604 6.75l.865-.5A3.5 3.5 0 ' +
  '0 1 1 4.5h-2c0 1.002.27 1.942.738 2.75zM0 4.5h1A3.5 3.5 0 0 1 4.5 1v-2A5.5 5.5 0 0 0-1 ' +
  '4.5zm5.414 8.949-.914-.407-.913.407-.914.407c.704 1.581 2.95 1.582 3.654 0zM8.397 ' +
  '6.75v1a1 1 0 0 1-.913-1.406zl.914.407a1 1 0 0 0-.914-1.407zm0 0-.866-.501a1 1 0 0 0 ' +
  '.866 1.501zv-1a1 1 0 0 1 .865 1.5z'

// Two handles can share a page, so each needs its own copy of the exported id.
const maskId = `graphing-pin-mask-${useId()}`

function onClick(): void {
  emit('action')
}
</script>

<template>
  <button
    type="button"
    class="graphing-pin-handle"
    :class="`graphing-pin-handle--${variant}`"
    :aria-label="variant === 'add' ? addPinLabel : removePinLabel"
    @click.stop="onClick"
    @mousedown.stop
  >
    <svg class="graphing-pin-handle__svg" viewBox="0 0 9 15" fill="none" aria-hidden="true">
      <path class="graphing-pin-handle__body" :d="BODY" />
      <mask :id="maskId" fill="#fff">
        <path :d="SILHOUETTE" />
      </mask>
      <path class="graphing-pin-handle__outline" :d="OUTLINE" :mask="`url(#${maskId})`" />
    </svg>
  </button>
</template>

<style scoped>
.graphing-pin-handle {
  position: absolute;
  z-index: 3;
  margin: 0;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  transform: translate(-50%, -100%);
}

.graphing-pin-handle__svg {
  display: block;
  width: 9px;
  height: auto;
}

.graphing-pin-handle__body {
  fill: var(--graph-pin-color);
}

.graphing-pin-handle__outline {
  fill: var(--graph-pin-color);
}

.graphing-pin-handle:hover .graphing-pin-handle__body {
  fill: color-mix(in srgb, var(--color-white-100) 30%, var(--graph-pin-color));
}

body[data-theme='facelift'] {
  .graphing-pin-handle--add {
    --graph-pin-color: var(--color-conference-grey-70);
  }

  .graphing-pin-handle--remove {
    --graph-pin-color: var(--color-corporate-green-70);
  }
}

body[data-theme='modern-dark'] {
  .graphing-pin-handle--add {
    --graph-pin-color: var(--color-white-70);
  }

  .graphing-pin-handle--remove {
    --graph-pin-color: var(--color-corporate-green-50);
  }
}
</style>
