<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { useTemplateRef } from 'vue'

const width = defineModel<number>('width', { required: true })
const height = defineModel<number>('height', { required: true })

const box = useTemplateRef<HTMLDivElement>('box')
const { observe } = useResizeObserver(([entry]) => {
  if (entry) {
    width.value = Math.round(entry.contentRect.width)
    height.value = Math.round(entry.contentRect.height)
  }
})
observe(box)
</script>

<template>
  <div
    ref="box"
    class="ucl-resizable-preview"
    :style="{ width: `${Math.max(0, width)}px`, height: `${Math.max(0, height)}px` }"
  >
    <slot />
  </div>
</template>

<style scoped>
.ucl-resizable-preview {
  box-sizing: content-box;
  min-width: 32px;
  min-height: 32px;
  overflow: hidden;
  resize: both;
  border: 1px solid var(--ucl-elements-border-color);
}
</style>
