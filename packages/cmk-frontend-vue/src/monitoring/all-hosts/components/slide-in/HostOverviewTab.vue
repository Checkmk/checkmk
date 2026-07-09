<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLoading from '@/components/CmkLoading.vue'

import type { HostRef } from '@/monitoring/shared/api/types'

import HostSlideInPlaceholder from './HostSlideInPlaceholder.vue'

const props = defineProps<{ host: HostRef }>()

const { _t } = usei18n()

const loading = ref(true)

onMounted(async () => {
  await Promise.resolve(props.host)
  loading.value = false
})
</script>

<template>
  <CmkLoading v-if="loading" />
  <HostSlideInPlaceholder
    v-else
    :title="_t('Overview')"
    :description="
      _t(
        'An at-a-glance summary of %{host} will appear here, bringing the key host information together in one place.',
        { host: host.name }
      )
    "
    :sections="[
      _t('Host details (name, alias, primary IP address, site, folder)'),
      _t('Service summary with a state visualization'),
      _t('Contact groups and tags'),
      _t('Labels (discovered and explicit)'),
      _t('Relations placeholder')
    ]"
  />
</template>
