<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'

interface CollapsibleTitleProps {
  title: TranslatedString
  help_text?: TranslatedString | null
  open: boolean
}

interface CollapsibleTitleEmit {
  toggleOpen: []
}

defineProps<CollapsibleTitleProps>()
defineEmits<CollapsibleTitleEmit>()
</script>
<template>
  <div class="db-collapsible-title">
    <CmkCollapsibleTitle
      :title="title"
      :help_text="help_text || null"
      :open="open"
      @toggle-open="() => $emit('toggleOpen')"
    />
  </div>
</template>

<style scoped>
.db-collapsible-title {
  background-color: var(--ux-theme-6);
  padding-left: 10px;
}
</style>
