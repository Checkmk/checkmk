<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useDebounceFn } from 'cmk-ui-library/lib/useDebounce'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { computed, onMounted, ref, watch } from 'vue'

import { middleTruncate } from './middleWordTruncation'

const props = defineProps<{ title: string; isCompact?: boolean }>()

// The title wraps to at most this many lines; past that it is middle-truncated (see fitTitle)
const MAX_LINES = computed(() => (props.isCompact ? 1 : 2))

const rootEl = ref<HTMLElement | null>(null)
// A hidden twin used to trial-fit candidate strings without disturbing the rendered title
const probeEl = ref<HTMLElement | null>(null)

const displayTitle = ref(props.title)

// Fit the title into at most MAX_LINES lines at the current width by trial-fitting candidate strings
// in the hidden probe, then hand the measurement to middleTruncate to pick the largest fit
function fitTitle(): void {
  const root = rootEl.value
  const probe = probeEl.value
  if (root === null || probe === null) {
    return
  }
  const width = root.clientWidth
  if (width === 0) {
    // Not laid out yet (or a non-DOM test env): show the full title; the resize observer re-fits
    // once a real width arrives.
    displayTitle.value = props.title
    return
  }
  const lineHeight = Number.parseFloat(getComputedStyle(root).lineHeight)
  const maxHeight = Number.isFinite(lineHeight)
    ? lineHeight * MAX_LINES.value + 1
    : Number.POSITIVE_INFINITY
  probe.style.width = `${width}px`
  const fits = (text: string): boolean => {
    probe.textContent = text
    return probe.scrollHeight <= maxHeight
  }

  displayTitle.value = middleTruncate(props.title, fits)
  probe.textContent = ''
}

// Debounce the resize-observer driven fit: it rewrites the title's text (and so its height), which
// re-fires the observer - and GraphHeader observes this same element too. Running it synchronously in
// the observer callback re-enters that cycle every frame and locks the tab under a continuous resize.
// Deferring off the callback lets the browser settle and coalesces a resize burst into one fit.
const debouncedFitTitle = useDebounceFn(fitTitle, 100)
const { observe } = useResizeObserver(debouncedFitTitle)
observe(rootEl)

// Re-fit after the rendered title or its font size (compact toggle) has settled in the DOM. The first
// fit runs synchronously so the title is shaped correctly on first paint, not after the debounce.
watch(() => props.title, fitTitle, { flush: 'post' })
watch(() => props.isCompact, fitTitle, { flush: 'post' })
onMounted(fitTitle)
</script>

<template>
  <div
    ref="rootEl"
    class="graphing-graph-title"
    :class="{ 'graphing-graph-title--compact': !!isCompact }"
    :title="title"
  >
    {{ displayTitle }}
    <span ref="probeEl" class="graphing-graph-title__probe" aria-hidden="true" />
  </div>
</template>

<style scoped>
.graphing-graph-title {
  position: relative;
  font-size: var(--font-size-large);
  font-weight: var(--font-weight-bold);

  /* Explicit so GraphHeader can read the title's line count and fitTitle can size its line box. */
  line-height: 1.4;
}

.graphing-graph-title--compact {
  font-size: var(--font-size-xsmall);
}

/* Off-screen measuring twin: inherits the title's typography and wrapping; its width is set in script. */
.graphing-graph-title__probe {
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  visibility: hidden;
  pointer-events: none;
}
</style>
