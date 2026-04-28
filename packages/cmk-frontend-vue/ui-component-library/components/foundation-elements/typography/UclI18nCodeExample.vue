<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()
</script>

<template>
  <CmkParagraph>{{ _t('Hello %{name}!', { name: 'Alice' }) }}</CmkParagraph>
</template>
