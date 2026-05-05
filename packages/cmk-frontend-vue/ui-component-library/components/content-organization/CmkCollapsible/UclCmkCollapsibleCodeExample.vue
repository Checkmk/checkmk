<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkCollapsible, { CmkCollapsibleTitle } from '@/components/CmkCollapsible'
import CmkIndent from '@/components/CmkIndent.vue'

const isOpen = ref(false)
</script>

<template>
  <CmkCollapsibleTitle
    title="Collapsible Section"
    side-title="Details"
    help-text="Click to expand"
    :open="isOpen"
    @toggle-open="isOpen = !isOpen"
  />

  <CmkCollapsible :open="isOpen">
    <CmkIndent>
      This content is hidden inside the collapsible wrapper. It animates height smoothly when
      toggled.
    </CmkIndent>
  </CmkCollapsible>
</template>
