<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCollapsibleTitle from '../CmkCollapsibleTitle.vue'
import CmkCollapsible from '../CmkCollapsible.vue'
import CmkIndent from '../CmkIndent.vue'
import { ref } from 'vue'

defineProps<{ screenshotMode: boolean }>()

const open = ref(false)
</script>

<template>
  <CmkCollapsibleTitle
    :title="'Collapsible Title'"
    :open="open"
    :help_text="'Some help text'"
    @toggle-open="open = !open"
  />
  <CmkCollapsible :open="open">
    <CmkIndent> Some text inside the collapsible </CmkIndent>
  </CmkCollapsible>
</template>
