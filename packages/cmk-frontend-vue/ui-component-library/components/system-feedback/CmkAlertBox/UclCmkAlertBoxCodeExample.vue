<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

const { _t } = usei18n()

const isOpen = ref(true)

const mainButton = {
  title: _t('Confirm'),
  onclick: () => {
    isOpen.value = false
  }
}
const optionalButton = {
  title: _t('Dismiss'),
  icon: 'cancel' as const,
  onclick: () => {
    isOpen.value = false
  }
}
</script>

<template>
  <CmkAlertBox
    v-if="isOpen"
    variant="warning"
    size="medium"
    heading="Confirm deletion"
    :main-button="mainButton"
    :optional-button="optionalButton"
  >
    This action cannot be undone. Are you sure you want to continue?
  </CmkAlertBox>
</template>
