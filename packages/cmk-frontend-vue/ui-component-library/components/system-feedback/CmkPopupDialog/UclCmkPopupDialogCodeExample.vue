<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'

const isOpen = ref(false)
</script>

<template>
  <CmkButton @click="isOpen = true"> Open Dialog </CmkButton>

  <CmkPopupDialog
    :open="isOpen"
    title="System Notification"
    text="This is a detailed message explaining the context of the dialog."
    icon="alert-crit"
    ok-button-text="OK Button Text"
    @close="isOpen = false"
  />
</template>
