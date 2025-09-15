/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export function randomId(len: number = 16, prefix: string = ''): string {
  const charset = '-abcdefghijklmnopqrstuvwxyz0123456789'
  const array = new Uint8Array(len)
  window.crypto.getRandomValues(array)
  let id = prefix ? prefix.concat('-') : ''
  for (let i = 0; i < len; i++) {
    id += charset.charAt((array[i] || 0) % charset.length)
  }

  return id
}
