<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface Props {
  min?: number
  max?: number
  step?: number
}

const props = withDefaults(defineProps<Props>(), {
  min: 0,
  max: 100,
  step: 1
})

const modelValue = defineModel<number>({ default: 50 })

const isDragging = ref(false)
const sliderRef = ref<HTMLElement>()
const inputValue = ref(modelValue.value.toString())

const percentage = computed(() => {
  return ((modelValue.value - props.min) / (props.max - props.min)) * 100
})

const updateValue = (value: number) => {
  const clampedValue = Math.max(props.min, Math.min(props.max, value))
  modelValue.value = clampedValue
  inputValue.value = clampedValue.toString()
}

const handleMouseDown = (event: MouseEvent) => {
  event.preventDefault()
  isDragging.value = true
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleMouseMove = (event: MouseEvent) => {
  if (!isDragging.value || !sliderRef.value) {
    return
  }

  const rect = sliderRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
  const value = Math.round((percentage / 100) * (props.max - props.min) + props.min)
  updateValue(value)
}

const handleMouseUp = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

const handleTrackClick = (event: MouseEvent) => {
  if (!sliderRef.value) {
    return
  }
  const rect = sliderRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
  const value = Math.round((percentage / 100) * (props.max - props.min) + props.min)
  updateValue(value)
}

const handleInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const value = target.value

  if (value === '') {
    inputValue.value = ''
    return
  }

  const numValue = parseFloat(value)
  if (!isNaN(numValue)) {
    updateValue(numValue)
  }
}

const handleInputBlur = () => {
  if (inputValue.value === '') {
    inputValue.value = modelValue.value.toString()
  }
}

watch(modelValue, (newValue) => {
  inputValue.value = newValue.toString()
})
</script>

<template>
  <div class="slider-group">
    <div class="slider-container">
      <div ref="sliderRef" class="slider-root" @click="handleTrackClick">
        <div class="slider-track">
          <div class="slider-range" :style="{ width: `${percentage}%` }"></div>
        </div>
        <div
          class="slider-thumb"
          :style="{ left: `${percentage}%` }"
          @mousedown="handleMouseDown"
        ></div>
      </div>
      <input
        v-model="inputValue"
        class="slider-value"
        type="number"
        :min="props.min"
        :max="props.max"
        :step="props.step"
        @input="handleInputChange"
        @blur="handleInputBlur"
      />
    </div>
  </div>
</template>

<style scoped>
.slider-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.slider-container {
  display: flex;
  align-items: center;
  gap: var(--dimension-5);
}

.slider-root {
  position: relative;
  flex: 1;
  height: var(--dimension-7);
  cursor: pointer;
  user-select: none;
}

.slider-track {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: var(--dimension-2);
  border-radius: 9999px;
  transform: translateY(-50%);
}

.slider-range {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background-color: var(--color-corporate-green-50);
  border-radius: 9999px;
  transition: width 0.1s ease;
}

.slider-thumb {
  position: absolute;
  top: 50%;
  width: var(--dimension-7);
  height: var(--dimension-7);
  background-color: var(--color-corporate-green-60);
  border-radius: 50%;
  cursor: grab;
  transform: translate(-50%, -50%);
  transition: box-shadow 150ms ease;
}

.slider-thumb:active {
  cursor: grabbing;
}

.slider-value {
  font-size: var(--dimension-5);
  color: var(--font-color);
  min-width: var(--dimension-9);
  width: var(--dimension-11);
  text-align: right;
  border: var(--font-color);
  outline: none;
  padding: 0;
}

.slider-value:focus {
  color: var(--font-color);
  border: 1px solid var(--font-color);
  border-radius: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-3);
}
</style>
