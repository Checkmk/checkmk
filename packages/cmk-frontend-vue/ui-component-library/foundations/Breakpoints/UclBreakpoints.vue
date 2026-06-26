<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import { computed, onMounted, ref, useTemplateRef } from 'vue'

import { useResizeObserver } from '@/lib/useResizeObserver'

import codeExample from './UclBreakpointsCodeExample.vue?raw'

defineProps<{ screenshotMode: boolean }>()

const BREAKPOINT_NAMES = ['xs', 's', 'm', 'l', 'xl'] as const
type BreakpointName = (typeof BREAKPOINT_NAMES)[number]

// Read the canonical pixel values from --breakpoint-* at runtime so this
// showcase never drifts from the SCSS source it teaches.
const breakpointsPx = ref<Record<BreakpointName, number>>({} as Record<BreakpointName, number>)

// containerWidth is the slider's authored value; measuredWidth is what the
// ResizeObserver reads back from the rendered element. They tick in lockstep
// but the demo shows the measured value because that is what @container
// queries actually react to (layout-rounded, post-zoom, etc.).
const containerWidth = ref(800)
const measuredWidth = ref(800)
const containerEl = useTemplateRef<HTMLElement>('containerEl')

const { observe } = useResizeObserver((entries) => {
  for (const entry of entries) {
    measuredWidth.value = Math.round(entry.contentRect.width)
  }
})
observe(containerEl)

onMounted(() => {
  const rootStyle = getComputedStyle(document.documentElement)
  breakpointsPx.value = Object.fromEntries(
    BREAKPOINT_NAMES.map((name) => [
      name,
      parseInt(rootStyle.getPropertyValue(`--breakpoint-${name}`), 10)
    ])
  ) as Record<BreakpointName, number>
})

const activeContainerBreakpoint = computed<BreakpointName | null>(() => {
  let active: BreakpointName | null = null
  for (const name of BREAKPOINT_NAMES) {
    const px = breakpointsPx.value[name]
    if (px !== undefined && measuredWidth.value >= px) {
      active = name
    }
  }
  return active
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>Breakpoints</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-breakpoints">
        <p class="ucl-breakpoints__hint">
          Drag the slider to resize the container below. The grid inside reflows at each
          <code>@container</code> breakpoint, independent of the browser window.
        </p>

        <label class="ucl-breakpoints__slider">
          <span>Container width: {{ containerWidth }}px</span>
          <input
            v-model.number="containerWidth"
            type="range"
            min="240"
            max="1300"
            step="10"
            aria-label="Demo container width"
          />
        </label>

        <div
          ref="containerEl"
          class="ucl-breakpoints__container"
          :style="{ width: `${containerWidth}px` }"
        >
          <div class="ucl-breakpoints__container-inner">
            <div class="ucl-breakpoints__tag">
              measured: {{ measuredWidth }}px · active: {{ activeContainerBreakpoint ?? '—' }}
            </div>
            <div class="ucl-breakpoints__grid">
              <div v-for="i in 6" :key="i" class="ucl-breakpoints__card">Card {{ i }}</div>
            </div>
          </div>
        </div>
      </div>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.ucl-breakpoints {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  width: 100%;
}

.ucl-breakpoints__hint {
  margin: 0;
  color: var(--font-color-dimmed);
}

.ucl-breakpoints__slider {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  font-weight: var(--font-weight-bold);
}

.ucl-breakpoints__slider input {
  width: 100%;
}

.ucl-breakpoints__container {
  container-type: inline-size;
  box-sizing: border-box;
  border: 1px dashed var(--default-border-color);
  border-radius: var(--dimension-3);
  background: var(--ux-theme-2);
  min-width: 240px;
}

.ucl-breakpoints__container-inner {
  padding: var(--dimension-5);
}

.ucl-breakpoints__tag {
  margin-bottom: var(--dimension-5);
  font-family: var(--font-family-monospace);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.ucl-breakpoints__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--dimension-4);

  @include bp.container-up(s) {
    grid-template-columns: 1fr 1fr;
  }

  @include bp.container-up(m) {
    grid-template-columns: repeat(3, 1fr);
  }

  @include bp.container-up(l) {
    grid-template-columns: repeat(4, 1fr);
  }

  @include bp.container-up(xl) {
    grid-template-columns: repeat(6, 1fr);
  }
}

.ucl-breakpoints__card {
  padding: var(--dimension-6);
  background: var(--ux-theme-4);
  border-radius: var(--dimension-3);
  text-align: center;
}
</style>
