<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { defineComponent } from 'vue'
import { useErrorBoundary } from '@/components/useErrorBoundary'
import { CmkError } from '@/lib/error.ts'
const props = defineProps<{ screenshotMode: boolean }>()

class DemoError<T extends Error> extends CmkError<T> {
  override name = 'DemoError'
  override getContext(): string {
    return 'DemoErrorContext'
  }
}

function throwCmkError() {
  try {
    try {
      throw new Error('something happened in code we can not control')
    } catch (error: unknown) {
      throw new DemoError('internal error handler, but keeps bubbeling', error as Error)
    }
  } catch (error: unknown) {
    throw new CmkError('this is a cmk error', error as Error)
  }
}

function throwError(message: string) {
  throw new Error(message)
}

// eslint-disable-next-line @typescript-eslint/naming-convention
const ScreenshotModeEnabler = defineComponent(() => {
  return () => {
    if (props.screenshotMode) {
      throwError('cheese')
    }
  }
}, {})

// eslint-disable-next-line @typescript-eslint/naming-convention
const { ErrorBoundary } = useErrorBoundary()
</script>

<template>
  <div>
    &lt;ErrorBoundary&gt;
    <ErrorBoundary>
      <button @click="throwError('this is a test error')">throw new Error()</button>
      <button @click="throwCmkError()">throw new CmkError()</button>
      <ScreenshotModeEnabler />
    </ErrorBoundary>
    &lt;/ErrorBoundary&gt;
  </div>
  <!-- I would have expected that this also triggers the onErrorCaptured method in useErrorBoundary, but its also fine this way -->
  <button @click="throwError('another error')">throw new Error() outside error boundary</button>
</template>

<style scoped></style>
