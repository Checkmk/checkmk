<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

interface AddFilterMessageProps {
  label?: TranslatedString
}

defineProps<AddFilterMessageProps>()
</script>
<template>
  <div class="db-add-filter-message__container">
    <div class="db-add-filter-message__inner">
      <CmkParagraph>{{ label ?? _t('Add filter from left panel') }}</CmkParagraph>
    </div>
  </div>
</template>

<style scoped>
.db-add-filter-message__container {
  padding: var(--dimension-4);
  color: var(--font-color-breadcrumb-inactive);
  background-color: var(--ux-theme-3);
}

.db-add-filter-message__inner {
  border: var(--dimension-1) dashed var(--dashed-border-color);
  background-color: var(--ux-theme-2);
  padding: var(--dimension-4);
}
</style>
