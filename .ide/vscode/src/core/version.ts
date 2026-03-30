export function parseVersion(ver: string): { major: number; minor: number; patch: number } {
  const parts = ver.split('.').map(Number)
  return { major: parts[0] || 0, minor: parts[1] || 0, patch: parts[2] || 0 }
}

/** Returns true if version `a` is strictly newer than version `b`. */
export function versionNewer(a: string, b: string): boolean {
  const va = parseVersion(a)
  const vb = parseVersion(b)
  if (va.major !== vb.major) return va.major > vb.major
  if (va.minor !== vb.minor) return va.minor > vb.minor
  return va.patch > vb.patch
}

/** Returns true if `ver` is at least `minVer` (>=). */
export function versionAtLeast(ver: string, minVer: string): boolean {
  const v = parseVersion(ver)
  const m = parseVersion(minVer)
  if (v.major !== m.major) return v.major > m.major
  if (v.minor !== m.minor) return v.minor > m.minor
  return v.patch >= m.patch
}
