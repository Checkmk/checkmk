<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'

import { useToast } from '@/maps/services/context'

const { toasts } = useToast()
</script>

<template>
  <Teleport to="#app">
    <!-- Live region: toasts are the SPA's only success/error feedback channel,
         so screen readers must announce them. -->
    <div class="maps-toast-container" role="status" aria-live="polite">
      <TransitionGroup name="maps-toast-container__toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="maps-toast-container__toast"
          :class="`maps-toast-container__toast--${toast.type}`"
        >
          <CmkIcon
            :name="toast.type === 'success' ? 'checkmark' : 'warning'"
            size="small"
            class="maps-toast-container__toast-icon"
          />
          <span>{{ toast.message }}</span>
          <button
            v-if="toast.action"
            type="button"
            class="maps-toast-container__toast-action"
            @click="toast.action.onClick()"
          >
            {{ toast.action.label }}
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.maps-toast-container {
  position: fixed;
  right: var(--dimension-7);
  bottom: var(--dimension-7);
  z-index: 200;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  pointer-events: none;
}

.maps-toast-container__toast {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing);
  max-width: 384px;
  padding: 12px 16px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  background: var(--ux-theme-3);
  border-radius: 12px;
  pointer-events: auto;
}

.maps-toast-container__toast--success {
  color: var(--color-corporate-green-50);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.maps-toast-container__toast--error {
  color: var(--color-light-red-40);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 30%, transparent),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.maps-toast-container__toast--warning {
  color: var(--color-warning);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent),
    0 20px 25px -5px rgb(0 0 0 / 40%),
    0 8px 10px -6px rgb(0 0 0 / 40%);
}

.maps-toast-container__toast-icon {
  flex-shrink: 0;
  margin-top: var(--dimension-2);
}

.maps-toast-container__toast-action {
  margin-left: var(--dimension-3);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.maps-toast-container__toast-action:hover {
  text-decoration: none;
}

.maps-toast-container__toast-enter-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.maps-toast-container__toast-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.maps-toast-container__toast-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.maps-toast-container__toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
