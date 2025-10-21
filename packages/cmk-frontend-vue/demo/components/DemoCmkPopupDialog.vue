<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopupDialog from '@/components/CmkPopupDialog.vue'

defineProps<{ screenshotMode: boolean }>()

const popupOpen = ref<boolean>(true)
</script>

<template>
  <CmkButton
    @click="
      () => {
        popupOpen = true
      }
    "
  >
    Open popup
  </CmkButton>
  <CmkPopupDialog
    :open="popupOpen"
    title="Test Title"
    text="Lorem Ipsum asasdasdfasfd asf asfasf af"
    icon="alert-crit"
    ok-button-text="Close"
    @close="popupOpen = false"
  />
</template>
