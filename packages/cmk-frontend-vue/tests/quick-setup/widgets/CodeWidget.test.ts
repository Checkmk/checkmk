/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import CodeWidget from '@/quick-setup/components/quick-setup/widgets/CodeWidget.vue'

test('code is displayed as text and the complete file can be downloaded', () => {
  const code = `value: "<strong>not markup</strong>"\n${'more: data\n'.repeat(15)}last: visible`
  render(CodeWidget, { props: { title: 'values.yaml', code, download_filename: 'values.yaml' } })

  expect(screen.getByRole('heading', { name: 'values.yaml' })).toBeVisible()
  expect(screen.getByText(/<strong>not markup<\/strong>/)).toBeVisible()
  expect(screen.getByText(/last: visible/)).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument()
  const download = screen.getByRole('link', { name: 'Download' })
  expect(download).toHaveAttribute('download', 'values.yaml')
  expect(download).toHaveAttribute(
    'href',
    `data:text/plain;charset=utf-8,${encodeURIComponent(code)}`
  )
})

test('commands without a filename have no download link', () => {
  render(CodeWidget, { props: { title: 'Install', code: 'helm upgrade --install example' } })

  expect(screen.getByRole('heading', { name: 'Install' })).toBeVisible()
  expect(screen.getByText('helm upgrade --install example')).toBeVisible()
  expect(screen.queryByRole('link', { name: 'Download' })).not.toBeInTheDocument()
})
