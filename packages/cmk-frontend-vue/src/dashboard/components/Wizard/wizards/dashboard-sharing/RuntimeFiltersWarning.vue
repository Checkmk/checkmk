<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkDialog from '@/components/CmkDialog.vue'

const { _t } = usei18n()

interface RuntimeFiltersWarningEmits {
  reviewFilters: []
}

defineEmits<RuntimeFiltersWarningEmits>()
</script>

<template>
  <CmkDialog
    :title="_t('Public link can\'t be generated')"
    :message="
      _t(
        'Public dashboards are view-only and don\'t support runtime filters.\nRemove runtime filters or convert them to default filters to continue.'
      )
    "
    :buttons="[
      { title: _t('Review filters'), onclick: () => $emit('reviewFilters'), variant: 'danger' }
    ]"
    :variant="'error'"
  />
</template>
