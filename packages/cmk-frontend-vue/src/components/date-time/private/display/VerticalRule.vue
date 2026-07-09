<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <div class="cmk-vertical-rule" role="separator" aria-orientation="vertical" />
</template>

<style scoped>
/* The horizontal counterpart to HorizontalRule; fills the row's height via the layout's stretch. */
.cmk-vertical-rule {
  align-self: stretch;
  width: 1px;
  background: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .cmk-vertical-rule {
  background: var(--color-mid-grey-90);
}
</style>
