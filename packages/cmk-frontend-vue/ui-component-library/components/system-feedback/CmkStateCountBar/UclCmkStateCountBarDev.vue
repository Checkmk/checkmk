<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{ screenshotMode: boolean }>()

const { _t } = usei18n()

const mix: StateSegment[] = [
  { label: _t('OK'), count: 24, color: 'success' },
  { label: _t('WARN'), count: 3, color: 'warning' },
  { label: _t('CRIT'), count: 1, color: 'danger' },
  { label: _t('UNKNOWN'), count: 0, color: 'unknown' },
  { label: _t('PENDING'), count: 2, color: 'default' }
]

const variants: { title: string; segments: StateSegment[] }[] = [
  {
    title: 'Typical mix',
    segments: mix
  },
  {
    title: 'Single state',
    segments: [
      { label: _t('OK'), count: 42, color: 'success' },
      { label: _t('WARN'), count: 0, color: 'warning' },
      { label: _t('CRIT'), count: 0, color: 'danger' },
      { label: _t('UNKNOWN'), count: 0, color: 'unknown' },
      { label: _t('PENDING'), count: 0, color: 'default' }
    ]
  },
  {
    title: 'Large counts',
    segments: [
      { label: _t('OK'), count: 1284, color: 'success' },
      { label: _t('WARN'), count: 57, color: 'warning' },
      { label: _t('CRIT'), count: 213, color: 'danger' },
      { label: _t('UNKNOWN'), count: 9, color: 'unknown' },
      { label: _t('PENDING'), count: 31, color: 'default' }
    ]
  },
  {
    title: 'All zero',
    segments: [
      { label: _t('OK'), count: 0, color: 'success' },
      { label: _t('WARN'), count: 0, color: 'warning' },
      { label: _t('CRIT'), count: 0, color: 'danger' },
      { label: _t('UNKNOWN'), count: 0, color: 'unknown' },
      { label: _t('PENDING'), count: 0, color: 'default' }
    ]
  }
]
</script>

<template>
  <div class="ucl-cmk-state-count-bar-dev">
    <div v-for="variant in variants" :key="variant.title" class="ucl-cmk-state-count-bar-dev__item">
      <h4 class="ucl-cmk-state-count-bar-dev__title">{{ variant.title }}</h4>
      <CmkStateCountBar :segments="variant.segments" />
    </div>
    <div class="ucl-cmk-state-count-bar-dev__item">
      <h4 class="ucl-cmk-state-count-bar-dev__title">Size medium (default)</h4>
      <CmkStateCountBar :segments="mix" size="medium" />
    </div>
    <div class="ucl-cmk-state-count-bar-dev__item">
      <h4 class="ucl-cmk-state-count-bar-dev__title">Size small</h4>
      <CmkStateCountBar :segments="mix" size="small" />
    </div>
  </div>
</template>

<style scoped>
.ucl-cmk-state-count-bar-dev {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-6);
  width: 320px;
}

.ucl-cmk-state-count-bar-dev__title {
  margin: 0 0 var(--dimension-4);
}
</style>
