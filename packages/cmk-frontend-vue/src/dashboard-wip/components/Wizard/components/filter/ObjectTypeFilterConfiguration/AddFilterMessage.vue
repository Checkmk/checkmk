<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()
</script>
<template>
  <div class="db-add-filter-message">
    <CmkParagraph>{{ _t('Select from list') }}</CmkParagraph>
  </div>
</template>

<style scoped>
.db-add-filter-message {
  border: var(--ux-theme-8) 1px dashed;
  margin: var(--spacing);
  padding: var(--spacing-double);
}
</style>
