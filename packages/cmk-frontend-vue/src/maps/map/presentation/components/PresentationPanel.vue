<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The chrome every floating surface of the presentation editor wears -- the
insert palette, the align bar, the history bar, the layers panel, the connect
bar and its popover.

It only paints the surface; where each of them sits, and how it lays its
contents out, stays with the panel itself (its own class lands on this root
through Vue's attribute fallthrough).
-->
<template>
  <div class="maps-presentation-panel">
    <slot />
  </div>
</template>

<style scoped>
.maps-presentation-panel {
  border-radius: var(--border-radius);
  background: var(--ux-theme-3);
  border: 1px solid var(--default-border-color);
  box-shadow: var(--maps-shadow-canvas-overlay-high);
}
</style>
