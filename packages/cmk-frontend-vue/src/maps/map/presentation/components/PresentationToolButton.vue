<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One button of the presentation editor's floating toolbars. The glyphs are the
design-tool vocabulary (shapes, alignment, layers, connect) that Checkmk's own
icon set does not carry, so they are inline SVG rather than ``CmkIcon``.

The slot is for an overlay badge, e.g. the count of slots still to connect.
-->
<script setup lang="ts">
import PresentationGlyph from './PresentationGlyph.vue'

defineProps<{
  /** Inline SVG glyph, from the ``ICONS`` constants. */
  icon: string
  title: string
  /** Renders the button as switched on (a panel it opens is showing). */
  active?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button
    class="maps-presentation-tool-button"
    :class="{ 'maps-presentation-tool-button--active': active }"
    :title="title"
    :aria-label="title"
    :aria-pressed="active"
    :disabled="disabled"
    @pointerdown.stop
  >
    <PresentationGlyph :svg="icon" />
    <slot />
  </button>
</template>

<style scoped>
.maps-presentation-tool-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--font-color);
  cursor: pointer;
}

.maps-presentation-tool-button:disabled {
  opacity: 0.35;
  cursor: default;
}

.maps-presentation-tool-button:hover:not(:disabled) {
  background: var(--input-hover-bg-color);
}

.maps-presentation-tool-button--active {
  background: color-mix(in srgb, var(--color-corporate-green-50) 18%, transparent);
}
</style>
