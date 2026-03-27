<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import UclFooter from '../UclFooter.vue'
</script>

<template>
  <div class="ucl-detail-page-layout">
    <slot />
    <UclFooter
      title="Design System documentation"
      subtitle="Explore detailed guidelines, usage principles, and processes in our Design System documentation. This space provides additional context to help you design, build, and maintain consistent components."
      button-text="View documentation"
      button-url="https://wiki.lan.checkmk.net/spaces/DS/pages/190552500/Components"
    />
  </div>
</template>

<style scoped>
.ucl-detail-page-layout {
  display: flex;
  flex-direction: column;
  padding: var(--dimension-6);
}

.ucl-detail-page-layout > * + * {
  margin-top: 24px;
}
</style>
