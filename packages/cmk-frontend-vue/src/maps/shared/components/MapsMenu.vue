<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A menu opened by a right-click on the map: at the pointer, over the canvas, with
the entries the caller puts in the ``default`` slot as MapsMenuItems.

What is clicked is drawn on a canvas, so there is no element for the focus to
come back to: it moves into the menu when the menu opens, and the arrow keys walk
the entries from there. Escape closes it.
-->
<script setup lang="ts">
import { useTemplateRef, watch } from 'vue'

import { usePointerOverlayStyle } from '@/maps/utils/overlayFrame'

const props = defineProps<{
  /** Where the operator right-clicked, in viewport coordinates. */
  x: number
  y: number
  /** Names the menu for assistive technology. */
  label: string
  /** What was clicked, shown above the entries. */
  heading?: string | undefined
  /** What kind of thing that is. */
  subheading?: string | undefined
}>()

const emit = defineEmits<{ close: [] }>()

const menuEl = useTemplateRef('menuEl')
const menuStyle = usePointerOverlayStyle(menuEl, () => ({ x: props.x, y: props.y }))

function entries(): HTMLElement[] {
  return Array.from(menuEl.value?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
}

// Only once it is placed: until then it is hidden, and a hidden element cannot
// take the focus.
const stopFocusing = watch(
  menuStyle,
  (style) => {
    if (style.visibility === 'hidden') {
      return
    }
    ;(entries()[0] ?? menuEl.value)?.focus()
    stopFocusing()
  },
  { flush: 'post' }
)

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
    return
  }
  const items = entries()
  if (items.length === 0) {
    return
  }
  const at = items.indexOf(document.activeElement as HTMLElement)
  const next: Record<string, number> = {
    ArrowDown: (at + 1) % items.length,
    ArrowUp: (at - 1 + items.length) % items.length,
    Home: 0,
    End: items.length - 1
  }
  const target = next[e.key]
  if (target !== undefined) {
    e.preventDefault()
    items[target]?.focus()
  }
}
</script>

<template>
  <div
    ref="menuEl"
    class="maps-menu"
    role="menu"
    :aria-label="label"
    tabindex="-1"
    :style="menuStyle"
    @keydown="onKeydown"
  >
    <div v-if="heading" class="maps-menu__header">
      <p class="maps-menu__name">{{ heading }}</p>
      <p v-if="subheading" class="maps-menu__type">{{ subheading }}</p>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.maps-menu {
  position: fixed;
  z-index: 50;
  width: max-content;
  min-width: 192px;
  max-width: calc(100% - 16px);
  padding: 6px 0;
  background: var(--maps-map-view-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.maps-menu:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-menu__header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  border-bottom: 1px solid var(--default-border-color);
}

.maps-menu__name {
  overflow: hidden;
  margin: 0;
  max-width: 208px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-menu__type {
  margin: var(--dimension-2) 0 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
