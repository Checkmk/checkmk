/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export function isValidIpOrHostname(value: string): boolean {
  const ipv4Match = value.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
  if (ipv4Match) {
    return ipv4Match.slice(1).every((p) => parseInt(p, 10) <= 255)
  }
  if (value.includes(':')) {
    return /^[0-9a-fA-F:]+$/.test(value) && value.split(':').length >= 2
  }
  const h = value.endsWith('.') ? value.slice(0, -1) : value
  if (!h || h.length > 253) {
    return false
  }
  const labels = h.split('.')
  if (/^\d+$/.test(labels[labels.length - 1] ?? '')) {
    return false
  }
  return labels.every((l) => l.length > 0 && /^(?!-)[a-z0-9-]{1,63}(?<!-)$/i.test(l))
}

export function isValidPort(value: number | undefined): boolean {
  return value !== undefined && Number.isInteger(value) && value >= 1 && value <= 65535
}

export function validateAddress(value: string, t: (s: string) => string): string[] {
  if (!value.trim()) {
    return [t('Enter a valid IP address or host name.')]
  }
  if (!isValidIpOrHostname(value.trim())) {
    return [t('Your input is not a valid host name or IP address.')]
  }
  return []
}

export function validatePort(value: number | undefined, t: (s: string) => string): string[] {
  if (!isValidPort(value)) {
    return [t('Enter a valid port number (example: 1234).')]
  }
  return []
}
