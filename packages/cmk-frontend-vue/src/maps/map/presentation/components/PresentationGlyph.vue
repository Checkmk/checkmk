<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// Renders a trusted, static inline SVG glyph. The markup comes exclusively from
// in-code constants (e.g. maps/map/presentation/chrome ICONS), never
// from user or backend data, so it is safe to inject. Centralising it here
// keeps the single required v-html sink in one reviewed place instead of
// scattering the toolbar/HUD glyphs across the canvas templates.
defineProps<{ svg: string }>()
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- trusted static inline SVG from code constants -->
  <span v-html="svg" />
</template>
