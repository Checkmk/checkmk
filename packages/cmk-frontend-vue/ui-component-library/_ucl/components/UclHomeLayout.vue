<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import UclFooter from './UclFooter.vue'
</script>

<template>
  <div class="ucl-home-layout">
    <header class="ucl-home-layout__header">
      <div class="ucl-home-layout__container">
        <slot name="header"></slot>
      </div>
    </header>

    <main class="ucl-home-layout__main ucl-home-layout__container">
      <section class="ucl-home-layout__section">
        <slot name="intro"></slot>
      </section>

      <section class="ucl-home-layout__section ucl-home-layout__feature-split">
        <div class="ucl-home-layout__feature-col feature-text">
          <slot name="feature-left"></slot>
        </div>
        <div class="ucl-home-layout__feature-col ucl-home-layout__feature-image">
          <slot name="feature-right"></slot>
        </div>
      </section>

      <section class="ucl-home-layout__section">
        <div class="ucl-home-layout__audience-header">
          <slot name="audience-title"></slot>
        </div>
        <div class="ucl-home-layout__audience-grid">
          <slot name="audience-cards"></slot>
        </div>
      </section>
    </main>

    <div class="ucl-home-layout__container ucl-home-layout__footer-wrapper">
      <UclFooter
        title="Design System documentation"
        subtitle="Explore detailed guidelines, usage principles, and processes in our Design System documentation. This space provides additional context to help you design, build, and maintain consistent components."
        button-text="View documentation"
        button-url="https://checkmk-int.atlassian.net/wiki/x/DwCGD"
      />
    </div>
  </div>
</template>

<style scoped>
.ucl-home-layout {
  --max-width: 90%;
  --spacing-section: 64px;

  line-height: 1.5;
}

.ucl-home-layout__container {
  width: 100%;
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 0 24px;
  box-sizing: border-box;
}

.ucl-home-layout__header {
  padding-top: 24px;
  margin-bottom: var(--spacing-section);
}

.ucl-home-layout__section {
  margin-bottom: var(--spacing-section);
}

.ucl-home-layout__section--last {
  margin-bottom: 0;
}

.ucl-home-layout__feature-split {
  display: flex;
  gap: 64px;
  align-items: center;
}

.ucl-home-layout__feature-col {
  flex: 1;
  min-width: 0;
}

.ucl-home-layout__feature-image {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.ucl-home-layout__audience-header {
  margin-bottom: 24px;
}

.ucl-home-layout__audience-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  width: 100%;
}

.ucl-home-layout__footer-wrapper {
  padding-bottom: 24px;
}

/* stylelint-disable selector-pseudo-class-no-unknown */
:deep(h1) {
  line-height: 1.2;
  margin-bottom: 16px;
}

:deep(h2) {
  margin-bottom: 12px;
  margin-top: 32px;
}

:deep(h2:first-child) {
  margin-top: 0;
}

:deep(p) {
  margin-bottom: 24px;
}

:deep(p:last-child) {
  margin-bottom: 0;
}

:deep(ul) {
  list-style-type: disc;
  padding-left: 20px;
  margin: 0 0 24px;
}

:deep(li) {
  margin-bottom: 4px;
}
/* stylelint-enable selector-pseudo-class-no-unknown */

@media (width < 1666px) {
  .ucl-home-layout__audience-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (width < 1024px) {
  .ucl-home-layout__feature-split {
    flex-direction: column;
  }

  .ucl-home-layout__audience-grid {
    grid-template-columns: 1fr;
  }
}
</style>
