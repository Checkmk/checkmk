<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed, onUnmounted, ref, watch } from 'vue'

const { detail, lastSuccessAt } = defineProps<{
  detail: string
  /** When data was last fetched, in milliseconds since the epoch. */
  lastSuccessAt?: number | undefined
}>()

const emit = defineEmits<{ retry: [] }>()

const { _t } = usei18n()

const AGE_UPDATE_INTERVAL_MS = 30_000

const now = ref(Date.now())
const ticker = setInterval(() => {
  now.value = Date.now()
}, AGE_UPDATE_INTERVAL_MS)
onUnmounted(() => clearInterval(ticker))
watch(
  () => lastSuccessAt,
  () => {
    now.value = Date.now()
  }
)

// Without an earlier success there is no age to tell, so the server's reason stands in.
const text = computed(() => {
  if (lastSuccessAt === undefined) {
    return untranslated(detail)
  }
  const minutes = Math.floor((now.value - lastSuccessAt) / 60_000)
  if (minutes < 1) {
    return _t('Last successful update less than a minute ago.')
  }
  return _t('Last successful update %{n} min ago.', { n: minutes })
})
</script>

<template>
  <CmkAlert
    variant="error"
    size="medium"
    :heading="_t('Data could not be loaded')"
    :text="text"
    :main-button="{ title: _t('Retry'), onclick: () => emit('retry') }"
  />
</template>
