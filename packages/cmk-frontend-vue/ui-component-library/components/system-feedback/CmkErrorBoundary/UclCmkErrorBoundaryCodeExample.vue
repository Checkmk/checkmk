<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

function throwError() {
  throw new Error('Something went wrong.')
}
</script>

<template>
  <CmkErrorBoundary>
    <button @click="throwError()">Throw error</button>
  </CmkErrorBoundary>
</template>
