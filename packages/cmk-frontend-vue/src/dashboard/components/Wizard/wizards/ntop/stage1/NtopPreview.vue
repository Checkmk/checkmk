<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

const { _t } = usei18n()
</script>

<template>
  <div class="db-ntop-preview">
    <div class="db-ntop-preview__msg">
      {{ _t('A preview of ntop widgets is not available due to the widget size limitation') }}
    </div>
  </div>
</template>

<style scoped>
.db-ntop-preview {
  --db-preview-content-height: calc(var(--dimension-8) * 10);
  --db-preview-content-padding: var(--dimension-3);

  display: flex;
  flex-direction: column;
  position: relative;
  height: var(--db-preview-content-height);
  margin: 0;
  padding: var(--db-preview-content-padding);
  box-sizing: border-box;
  background-color: var(--db-content-bg-color);
}

.db-ntop-preview__msg {
  width: 100%;
  text-align: center;
  margin: auto 0;
  line-height: var(--dimension-7);
}
</style>
