<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div class="widget">
    <div class="widget__grid">
      <div class="widget__card">Card 1</div>
      <div class="widget__card">Card 2</div>
      <div class="widget__card">Card 3</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.widget {
  container-type: inline-size;
  max-width: var(--breakpoint-xl);
}

.widget__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--dimension-4);

  @include bp.container-up(m) {
    grid-template-columns: 1fr 1fr 1fr;
  }
}

.widget__card {
  padding: var(--dimension-6);
  background: var(--ux-theme-4);
  border-radius: var(--dimension-3);
}
</style>
