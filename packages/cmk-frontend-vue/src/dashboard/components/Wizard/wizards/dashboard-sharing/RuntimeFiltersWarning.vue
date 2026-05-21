<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

const { _t } = usei18n()

interface RuntimeFiltersWarningEmits {
  reviewFilters: []
}

defineEmits<RuntimeFiltersWarningEmits>()
</script>

<template>
  <CmkAlertBox
    :heading="_t('Public link can\'t be generated')"
    :main-button="{ title: _t('Review filters'), onclick: () => $emit('reviewFilters') }"
    variant="error"
  >
    {{
      _t(
        "Public dashboards are view-only and don't support runtime filters.\nRemove runtime filters or convert them to default filters to continue."
      )
    }}
  </CmkAlertBox>
</template>
