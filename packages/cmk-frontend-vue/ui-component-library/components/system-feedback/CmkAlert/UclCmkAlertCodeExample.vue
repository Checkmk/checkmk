<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

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
  <CmkAlert
    v-if="isOpen"
    variant="warning"
    size="medium"
    heading="Confirm deletion"
    :main-button="mainButton"
    :optional-button="optionalButton"
  >
    This action cannot be undone. Are you sure you want to continue?
  </CmkAlert>
</template>
