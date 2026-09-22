<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type {
  ObjectState,
  PresentationElement,
  PresentationTheme,
  ShapeElement
} from '@/maps/types/api'

import { isUnboundSlot } from '../binding'
import { sampleStateFor } from '../sampleState'
import { themeTokens } from '../themes'
import PresentationElementView from './PresentationElementView.vue'

const props = withDefaults(
  defineProps<{
    elements: PresentationElement[]
    theme: PresentationTheme
    width?: number
    height?: number
    thumbWidth?: number
  }>(),
  { width: 1920, height: 1080, thumbWidth: 248 }
)

const scale = computed(() => props.thumbWidth / props.width)

const outerStyle = computed(() => ({
  width: `${props.thumbWidth}px`,
  height: `${Math.round(props.height * scale.value)}px`
}))

const stageStyle = computed(() => ({
  ...themeTokens(props.theme),
  width: `${props.width}px`,
  height: `${props.height}px`,
  transform: `scale(${scale.value})`,
  transformOrigin: 'top left'
}))

function isConnector(el: PresentationElement): el is ShapeElement {
  return el.kind === 'shape' && (el.shape === 'line' || el.shape === 'arrow')
}

function centerOf(id: string | null | undefined): { x: number; y: number } | null {
  const el = props.elements.find((e) => e.id === id)
  if (!el) {
    return null
  }
  return { x: el.x + el.w / 2, y: el.y + el.h / 2 }
}

const connectors = computed(() =>
  props.elements.filter(isConnector).map((el) => ({
    el,
    start: centerOf(el.start_ref) ?? { x: el.x, y: el.y },
    end: centerOf(el.end_ref) ?? { x: el.x + el.w, y: el.y + el.h }
  }))
)

const boxElements = computed(() =>
  [...props.elements]
    .filter((e) => !isConnector(e) && e.kind !== 'group' && !e.hidden)
    .sort((a, b) => a.z - b.z)
)

function elStyle(el: PresentationElement): Record<string, string> {
  return {
    left: `${el.x}px`,
    top: `${el.y}px`,
    width: `${el.w}px`,
    height: `${el.h}px`,
    opacity: String(el.opacity),
    transform: el.rotation ? `rotate(${el.rotation}deg)` : 'none',
    zIndex: String(el.z)
  }
}

// Built once per element rather than per render: the generator is called for
// every unbound slot, and a gallery shows a dozen slides at a time.
const sampleStates = computed(
  () =>
    new Map(props.elements.filter(isUnboundSlot).map((el) => [el.id, sampleStateFor(el)] as const))
)
function sampleFor(el: PresentationElement): ObjectState | undefined {
  return sampleStates.value.get(el.id)
}
</script>

<template>
  <div class="maps-presentation-slide-preview" :style="outerStyle">
    <div class="maps-presentation-slide-preview__stage" :style="stageStyle">
      <div class="maps-presentation-slide-preview__bg" />
      <svg
        class="maps-presentation-slide-preview__connectors"
        :style="{ width: `${width}px`, height: `${height}px` }"
      >
        <line
          v-for="c in connectors"
          :key="c.el.id"
          :x1="c.start.x"
          :y1="c.start.y"
          :x2="c.end.x"
          :y2="c.end.y"
          stroke="var(--pres-shape-stroke)"
          :stroke-width="c.el.stroke_width * 2"
          stroke-linecap="round"
        />
      </svg>
      <div
        v-for="el in boxElements"
        :key="el.id"
        class="maps-presentation-slide-preview__el"
        :style="elStyle(el)"
      >
        <PresentationElementView :element="el" :state="undefined" :sample-state="sampleFor(el)" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-presentation-slide-preview {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  pointer-events: none;
}

.maps-presentation-slide-preview__stage {
  position: absolute;
  top: 0;
  left: 0;
}

.maps-presentation-slide-preview__bg {
  position: absolute;
  inset: 0;
  background: var(--pres-bg);
}

.maps-presentation-slide-preview__connectors {
  position: absolute;
  inset: 0;
  overflow: visible;
}

.maps-presentation-slide-preview__el {
  position: absolute;
  transform-origin: center center;
}
</style>
