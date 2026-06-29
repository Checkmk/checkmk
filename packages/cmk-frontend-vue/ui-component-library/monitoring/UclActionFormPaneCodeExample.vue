<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import ActionFormPane from '@/monitoring/shared/components/action/ActionFormPane.vue'

const { _t } = usei18n()

const hostName = 'web-server-01' as TranslatedString
</script>

<template>
  <ActionFormPane
    :definition="{ type: 'comment', ident: 'comment' }"
    :title="_t('Add comment')"
    :subtitle="hostName"
    @submit="() => {}"
    @cancel="() => {}"
  />
</template>
