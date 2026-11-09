/** MessDeck logo mark: laptop dashboard + serving cloche inside a ring, with a leaf sprig. */
export function LogoMark({ className = '', light = false }: { className?: string; light?: boolean }) {
  const ink = light ? '#fef9ed' : '#1d3f24'
  const cutout = light ? '#132b18' : '#fef9ed'
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <path d="M17 9.5A28 28 0 1 0 47 9.5" fill="none" stroke={ink} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M12 21C7 13 10 6 19 4c1.5 8-1.5 14-7 17z" fill="#678234" />
      <path d="M17 18c-1-7 3-11 10-11-0.5 6-4 10-10 11z" fill="#86a24c" />
      <rect x="18" y="17" width="28" height="20" rx="2" fill="none" stroke={ink} strokeWidth="2.5" />
      <rect x="22" y="28" width="3" height="5" rx="0.5" fill="#678234" />
      <rect x="26.5" y="25" width="3" height="8" rx="0.5" fill="#678234" />
      <rect x="34" y="22" width="8" height="2" rx="1" fill="#678234" />
      <rect x="34" y="27" width="6" height="2" rx="1" fill="#678234" />
      <rect x="13" y="38.5" width="38" height="3" rx="1.5" fill={ink} />
      <path d="M22 47a10 10 0 0 1 20 0z" fill={ink} stroke={cutout} strokeWidth="1.5" paintOrder="stroke" />
      <circle cx="32" cy="36" r="1.6" fill={ink} stroke={cutout} strokeWidth="1" paintOrder="stroke" />
      <rect x="19" y="47.5" width="26" height="2.5" rx="1.25" fill={ink} />
    </svg>
  )
}

/** "MESSDECK" wordmark — the E is three bars with a leaf-green middle bar, as in the artwork. */
export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-baseline font-bold tracking-[0.08em] ${className}`}>
      <span aria-hidden="true" className="inline-flex items-baseline">
        M
        <svg viewBox="0 0 10 14" className="mx-[0.06em] h-[0.72em] w-auto">
          <rect x="0" y="0" width="10" height="2.2" fill="currentColor" />
          <rect x="0" y="5.9" width="10" height="2.2" fill="#678234" />
          <rect x="0" y="11.8" width="10" height="2.2" fill="currentColor" />
        </svg>
        SSDECK
      </span>
      <span className="sr-only">MessDeck</span>
    </span>
  )
}

export function Logo({ light = false, className = '' }: { light?: boolean; className?: string }) {
  return (
    <span className={`flex items-center gap-2 ${light ? 'text-cream' : 'text-brand-800'} ${className}`}>
      <LogoMark light={light} className="h-9 w-9 shrink-0" />
      <Wordmark className="text-xl" />
    </span>
  )
}
