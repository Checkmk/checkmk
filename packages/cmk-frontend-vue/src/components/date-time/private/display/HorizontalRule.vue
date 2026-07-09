<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts"></script>

<template>
  <hr class="cmk-horizontal-rule" aria-hidden="true" />
</template>

<style scoped>
/* Spacing is intentionally left to the surrounding layout's gap, so the UA margins are reset. */
.cmk-horizontal-rule {
  margin: 0;
  border: 0;
  width: 100%;
  height: 1px;
  background: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .cmk-horizontal-rule {
  background: var(--color-mid-grey-90);
}
</style>
