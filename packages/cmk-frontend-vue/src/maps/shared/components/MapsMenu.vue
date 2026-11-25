<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A menu opened by a right-click on the map: at the pointer, over the canvas, with
the entries the caller puts in the ``default`` slot as MapsMenuItems.

The focus moves into the menu when it opens, and the arrow keys walk the
entries from there. Escape or a click outside closes it. The focus goes back
where it was before, unless a click outside put it elsewhere: for an entry
before its action runs, so a dialog the action opens returns it there too.
-->
<script setup lang="ts">
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { onUnmounted, useTemplateRef, watch } from 'vue'

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

const vClickOutside = useClickOutside()

const menuEl = useTemplateRef('menuEl')
const menuStyle = usePointerOverlayStyle(menuEl, () => ({ x: props.x, y: props.y }))

let lastFocused: HTMLElement | null = null

function rememberOpener(): void {
  const active = document.activeElement
  if (active instanceof HTMLElement && !menuEl.value?.contains(active)) {
    lastFocused = active
  }
}
rememberOpener()

function focusFirstEntry(): void {
  ;(entries()[0] ?? menuEl.value)?.focus()
}

function restoreFocus(): void {
  if (lastFocused?.isConnected) {
    lastFocused.focus()
  }
  lastFocused = null
}

function onEntryClick(event: MouseEvent): void {
  if (event.target instanceof Element && event.target.closest('[role="menuitem"]')) {
    restoreFocus()
  }
}

function closeOnClickOutside(): void {
  lastFocused = null
  emit('close')
}

onUnmounted(restoreFocus)

// A right-click elsewhere while it is open moves it rather than remounting it:
// that is a new opening, from what was clicked now.
watch(
  [() => props.x, () => props.y],
  () => {
    rememberOpener()
    focusFirstEntry()
  },
  { flush: 'post' }
)

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
    focusFirstEntry()
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
    v-click-outside="{ open: true, close: closeOnClickOutside }"
    class="maps-menu"
    role="menu"
    :aria-label="label"
    tabindex="-1"
    :style="menuStyle"
    @keydown="onKeydown"
    @click.capture="onEntryClick"
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
  padding: var(--dimension-4) 0;
  background: var(--maps-map-view-overlay-bg);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    var(--maps-shadow-canvas-overlay-high);
}

.maps-menu:focus-visible {
  outline: revert;
  outline-offset: 2px;
}

.maps-menu__header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) var(--dimension-5);
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
