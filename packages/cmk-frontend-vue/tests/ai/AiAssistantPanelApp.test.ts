/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'

import AiAssistantPanelApp from '@/ai/AiAssistantPanelApp.vue'

const OPEN_STORAGE_KEY = 'cmk-ai-assistant-open'
const POSITION_STORAGE_KEY = 'cmk-ai-assistant-position'

function mainAreaInset(): Record<string, string> {
  const style = document.documentElement.style
  return {
    left: style.getPropertyValue('--main-area-inset-left'),
    right: style.getPropertyValue('--main-area-inset-right'),
    bottom: style.getPropertyValue('--main-area-inset-bottom')
  }
}

function renderOpenPanel(): void {
  sessionStorage.setItem(OPEN_STORAGE_KEY, 'true')
  render(AiAssistantPanelApp)
}

beforeEach(() => {
  sessionStorage.clear()
  localStorage.clear()
  document.documentElement.removeAttribute('style')
})

test('docks to the right by default', () => {
  renderOpenPanel()

  expect(screen.getByText('AI assistant').closest('.ai-assistant-panel-app')).toHaveClass(
    'ai-assistant-panel-app--right'
  )
  expect(mainAreaInset()).toEqual({ left: '0px', right: '300px', bottom: '0px' })
})

test('restores the stored docking edge and reserves the space there', () => {
  localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify('bottom'))

  renderOpenPanel()

  expect(screen.getByText('AI assistant').closest('.ai-assistant-panel-app')).toHaveClass(
    'ai-assistant-panel-app--bottom'
  )
  expect(mainAreaInset()).toEqual({ left: '0px', right: '0px', bottom: '300px' })
})

test('falls back to the right edge for an unknown stored position', () => {
  localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify('top'))

  renderOpenPanel()

  expect(mainAreaInset()).toEqual({ left: '0px', right: '300px', bottom: '0px' })
})

test('follows a docking edge changed in another frame', async () => {
  renderOpenPanel()

  window.dispatchEvent(
    new StorageEvent('storage', { key: POSITION_STORAGE_KEY, newValue: JSON.stringify('left') })
  )
  await screen.findByText('AI assistant')

  expect(screen.getByText('AI assistant').closest('.ai-assistant-panel-app')).toHaveClass(
    'ai-assistant-panel-app--left'
  )
  expect(mainAreaInset()).toEqual({ left: '300px', right: '0px', bottom: '0px' })
})

test('reserves no space while closed', () => {
  localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify('left'))

  render(AiAssistantPanelApp)

  expect(screen.queryByText('AI assistant')).not.toBeInTheDocument()
  expect(mainAreaInset()).toEqual({ left: '0px', right: '0px', bottom: '0px' })
})

test('moves the panel to the clicked edge and remembers it', async () => {
  renderOpenPanel()

  await fireEvent.click(screen.getByRole('button', { name: 'Dock to the left' }))

  expect(screen.getByText('AI assistant').closest('.ai-assistant-panel-app')).toHaveClass(
    'ai-assistant-panel-app--left'
  )
  expect(mainAreaInset()).toEqual({ left: '300px', right: '0px', bottom: '0px' })
  expect(JSON.parse(localStorage.getItem(POSITION_STORAGE_KEY)!)).toBe('left')
})

test('marks the current edge as pressed', async () => {
  renderOpenPanel()

  expect(screen.getByRole('button', { name: 'Dock to the right' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('button', { name: 'Dock to the bottom' })).toHaveAttribute(
    'aria-pressed',
    'false'
  )

  await fireEvent.click(screen.getByRole('button', { name: 'Dock to the bottom' }))

  expect(screen.getByRole('button', { name: 'Dock to the bottom' })).toHaveAttribute(
    'aria-pressed',
    'true'
  )
  expect(screen.getByRole('button', { name: 'Dock to the right' })).toHaveAttribute(
    'aria-pressed',
    'false'
  )
})

test('closes on Escape and releases the space', async () => {
  renderOpenPanel()

  await fireEvent.keyDown(window, { key: 'Escape' })

  expect(screen.queryByText('AI assistant')).not.toBeInTheDocument()
  expect(mainAreaInset()).toEqual({ left: '0px', right: '0px', bottom: '0px' })
  expect(JSON.parse(sessionStorage.getItem(OPEN_STORAGE_KEY)!)).toBe(false)
})
