/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MnemonicTitle from '@/main-menu/components/MnemonicTitle.vue'

describe('MnemonicTitle', () => {
  test('underlines the first occurrence of the mnemonic regardless of case', () => {
    render(MnemonicTitle, { props: { title: 'Monitor', mnemonic: 'm' } })

    expect(screen.getByText('M')).toHaveClass('mm-mnemonic-title__key')
  })

  test('shows the plain title when the mnemonic is not part of it', () => {
    const { container } = render(MnemonicTitle, { props: { title: 'Sidebar', mnemonic: '/' } })

    expect(container.querySelector('.mm-mnemonic-title__key')).toBeNull()
    expect(screen.getByText('Sidebar')).toBeInTheDocument()
  })
})
