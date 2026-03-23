<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import checkMKLogo from '../assets/images/checkmk-logo.svg'

defineProps<{
  title: string
  subtitle: string
}>()
</script>

<template>
  <div class="ucl-hero-banner">
    <div class="ucl-hero-banner__content">
      <div class="ucl-hero-banner__logo-box">
        <img :src="checkMKLogo" alt="Checkmk Logo" class="ucl-hero-banner__icon" />
      </div>
      <h1 class="ucl-hero-banner__title">{{ title }}</h1>
      <p class="ucl-hero-banner__subtitle">{{ subtitle }}</p>
    </div>
  </div>
</template>

<style scoped>
.ucl-hero-banner {
  background: linear-gradient(
    90deg,
    var(--color-midnight-grey-50),
    var(--color-corporate-green-60),
    var(--color-corporate-green-50)
  );
  border-radius: 4px;
  padding: 64px 32px;
  text-align: center;
}

@media (width < 1024px) {
  .ucl-hero-banner {
    background: linear-gradient(
      90deg,
      var(--color-corporate-green-70),
      var(--color-corporate-green-40)
    );
  }
}

.ucl-hero-banner__content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ucl-hero-banner__logo-box {
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.ucl-hero-banner__title {
  font-size: var(--ucl-font-size-h1-heading);
  font-weight: 800;
  margin: 0 0 8px;
  color: var(--color-white-100);
}

.ucl-hero-banner__subtitle {
  font-size: 16px;
  color: var(--color-white-100);
  margin: 0;
}
</style>
