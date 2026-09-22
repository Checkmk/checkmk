<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const { orientation = 'vertical' } = defineProps<{
  orientation?: 'horizontal' | 'vertical'
}>()
</script>

<template>
  <span class="cmk-resize-handle" :class="`cmk-resize-handle--${orientation}`" aria-hidden="true">
    <span class="cmk-resize-handle__line" />
    <span class="cmk-resize-handle__line" />
  </span>
</template>

<style scoped>
.cmk-resize-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  gap: var(--dimension-2);
  border: var(--dimension-1) solid var(--cmk-resize-handle-border-color);
  border-radius: var(--border-radius);
  background-color: var(--cmk-resize-handle-bg-color);
  cursor: col-resize;
}

.cmk-resize-handle--vertical {
  width: var(--dimension-6);
  height: var(--dimension-10);
}

.cmk-resize-handle--horizontal {
  width: var(--dimension-10);
  height: var(--dimension-6);
  flex-direction: column;
  cursor: row-resize;
}

.cmk-resize-handle__line {
  border-radius: var(--dimension-1);
  background-color: var(--cmk-resize-handle-line-color);
}

.cmk-resize-handle--vertical .cmk-resize-handle__line {
  width: var(--dimension-1);
  height: var(--dimension-5);
}

.cmk-resize-handle--horizontal .cmk-resize-handle__line {
  width: var(--dimension-5);
  height: var(--dimension-1);
}

.cmk-resize-handle:hover {
  background-image: linear-gradient(
    var(--cmk-resize-handle-hover-overlay),
    var(--cmk-resize-handle-hover-overlay)
  );
}

body[data-theme='facelift'] .cmk-resize-handle {
  --cmk-resize-handle-bg-color: var(--color-daylight-grey-60);
  --cmk-resize-handle-border-color: var(--color-mid-grey-50);
  --cmk-resize-handle-line-color: var(--color-mid-grey-100);
  --cmk-resize-handle-hover-overlay: var(--color-conference-grey-10);
}

body[data-theme='modern-dark'] .cmk-resize-handle {
  --cmk-resize-handle-bg-color: var(--color-midnight-grey-100);
  --cmk-resize-handle-border-color: var(--color-mid-grey-60);
  --cmk-resize-handle-line-color: var(--color-white-100);
  --cmk-resize-handle-hover-overlay: var(--color-white-10);
}
</style>
