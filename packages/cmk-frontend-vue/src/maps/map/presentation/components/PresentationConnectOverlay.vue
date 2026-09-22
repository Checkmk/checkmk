<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

export interface ConnectSlotBox {
  id: string
  x: number
  y: number
  w: number
  h: number
  // Stable session number — binding a slot must not renumber the others.
  n: number
  bound: boolean
}

const props = defineProps<{
  // Pre-resolved on-slide bounds (a connector's box spans its endpoints).
  slots: ConnectSlotBox[]
  currentId: string | null
  scale: number
}>()

const emit = defineEmits<{ pick: [string] }>()

// Slide-space overlay: outlines hug the slot's box; chrome (border, badge) is
// divided by the zoom factor so it keeps a constant on-screen size.
function slotStyle(box: ConnectSlotBox): Record<string, string> {
  return {
    left: `${box.x}px`,
    top: `${box.y}px`,
    width: `${box.w}px`,
    height: `${box.h}px`,
    borderWidth: `${2 / props.scale}px`,
    borderRadius: `${10 / props.scale}px`
  }
}

const badgeStyle = computed(() => ({
  width: `${26 / props.scale}px`,
  height: `${26 / props.scale}px`,
  fontSize: `${13 / props.scale}px`,
  top: `${-12 / props.scale}px`,
  left: `${-12 / props.scale}px`,
  borderWidth: `${2 / props.scale}px`
}))
</script>

<template>
  <div class="maps-presentation-connect-overlay">
    <div
      v-for="slot in slots"
      :key="slot.id"
      class="maps-presentation-connect-overlay__slot"
      :class="{
        'maps-presentation-connect-overlay__slot--current': slot.id === currentId,
        'maps-presentation-connect-overlay__slot--bound': slot.bound
      }"
      :style="slotStyle(slot)"
      @pointerdown.stop="!slot.bound && emit('pick', slot.id)"
    >
      <span
        class="maps-presentation-connect-overlay__badge"
        :class="{
          'maps-presentation-connect-overlay__badge--bound': slot.bound,
          'maps-presentation-connect-overlay__badge--current': slot.id === currentId && !slot.bound
        }"
        :style="badgeStyle"
      >
        {{ slot.bound ? '✓' : slot.n }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.maps-presentation-connect-overlay {
  position: absolute;
  inset: 0;
  z-index: 1002;
  pointer-events: none;
}

.maps-presentation-connect-overlay__slot {
  position: absolute;
  border-style: dashed;

  /* Waiting slots recede so the eye lands on the one current slot. */
  border-color: color-mix(in srgb, var(--pres-accent) 45%, transparent);
  cursor: pointer;
  pointer-events: auto;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}

.maps-presentation-connect-overlay__slot--bound {
  border-color: color-mix(in srgb, var(--pres-accent) 30%, transparent);
  cursor: default;
}

/* The current slot reads as "fill me now": solid border + accent tint, kept
   distinct without motion so it still stands out under prefers-reduced-motion. */
.maps-presentation-connect-overlay__slot--current {
  border-style: solid;
  border-color: var(--pres-accent);
  background: color-mix(in srgb, var(--pres-accent) 14%, transparent);
  animation: maps-presentation-connect-overlay-pulse 1.4s ease-in-out infinite;
}

@keyframes maps-presentation-connect-overlay-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--pres-accent) 70%, transparent);
  }

  50% {
    box-shadow: 0 0 0 12px color-mix(in srgb, var(--pres-accent) 0%, transparent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-presentation-connect-overlay__slot--current {
    animation: none;
  }
}

.maps-presentation-connect-overlay__badge {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-style: solid;
  border-color: var(--pres-bg);
  border-radius: 9999px;
  background: var(--pres-accent);
  color: var(--pres-bg);
  font-weight: var(--font-weight-bold);
}

.maps-presentation-connect-overlay__badge--bound {
  background: #22c55e;
}

/* Lift the current slot's number off the muted ones with a contrasting ring. */
.maps-presentation-connect-overlay__badge--current {
  box-shadow: 0 0 0 2px var(--pres-bg);
  outline: 2px solid var(--pres-accent);
}
</style>
