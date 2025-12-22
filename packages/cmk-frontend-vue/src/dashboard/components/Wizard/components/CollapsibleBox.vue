<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import CollapsibleContent from './collapsible/CollapsibleContent.vue'
import CollapsibleTitle from './collapsible/CollapsibleTitle.vue'

interface CollapsibleBoxProps {
  title: TranslatedString
  open?: boolean
  helpText?: TranslatedString
}

const props = defineProps<CollapsibleBoxProps>()

const isOpen = ref<boolean>(props?.open ?? true)
</script>

<template>
  <CollapsibleTitle
    :title="title"
    :help_text="helpText ?? null"
    :open="isOpen"
    @toggle-open="isOpen = !isOpen"
  />
  <CollapsibleContent :open="isOpen"><slot /></CollapsibleContent>
</template>
