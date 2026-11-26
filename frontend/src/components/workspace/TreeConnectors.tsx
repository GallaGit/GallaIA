import { useCallback, useEffect, useRef } from 'react'
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion'

type Props = {
  wrapRef: React.RefObject<HTMLDivElement | null>
  orqRef: React.RefObject<HTMLElement | null>
  feRef: React.RefObject<HTMLElement | null>
  beRef: React.RefObject<HTMLElement | null>
}

function anchor(
  wrap: DOMRect,
  el: HTMLElement,
  where: 'top' | 'bottom',
): { x: number; y: number } {
  const r = el.getBoundingClientRect()
  return {
    x: r.left - wrap.left + r.width / 2,
    y: where === 'bottom' ? r.bottom - wrap.top : r.top - wrap.top,
  }
}

function cubic(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  const span = Math.max(24, to.y - from.y)
  const dy = span * 0.55
  const fix = (n: number) => Math.round(n * 10) / 10
  return `M ${fix(from.x)},${fix(from.y)} C ${fix(from.x)},${fix(from.y + dy)} ${fix(to.x)},${fix(to.y - dy)} ${fix(to.x)},${fix(to.y)}`
}

/**
 * SVG connectors that track card geometry (boceto layoutConnectors).
 * Recalculates on resize / ResizeObserver; respects prefers-reduced-motion.
 */
export default function TreeConnectors({
  wrapRef,
  orqRef,
  feRef,
  beRef,
}: Props) {
  const pathFeRef = useRef<SVGPathElement>(null)
  const pathBeRef = useRef<SVGPathElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const reduced = usePrefersReducedMotion()

  const layout = useCallback(() => {
    const wrap = wrapRef.current
    const orq = orqRef.current
    const fe = feRef.current
    const be = beRef.current
    const svg = svgRef.current
    const pathFE = pathFeRef.current
    const pathBE = pathBeRef.current
    if (!wrap || !orq || !fe || !be || !svg || !pathFE || !pathBE) return

    const w = Math.max(1, wrap.clientWidth)
    const h = Math.max(1, wrap.clientHeight)
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`)
    svg.setAttribute('width', String(w))
    svg.setAttribute('height', String(h))

    const box = wrap.getBoundingClientRect()
    const start = anchor(box, orq, 'bottom')
    pathFE.setAttribute('d', cubic(start, anchor(box, fe, 'top')))
    pathBE.setAttribute('d', cubic(start, anchor(box, be, 'top')))
  }, [wrapRef, orqRef, feRef, beRef])

  useEffect(() => {
    layout()
    const raf = requestAnimationFrame(layout)
    window.addEventListener('resize', layout)

    const ro =
      typeof ResizeObserver !== 'undefined' ? new ResizeObserver(layout) : null
    const wrap = wrapRef.current
    const orq = orqRef.current
    const fe = feRef.current
    const be = beRef.current
    if (ro) {
      if (wrap) ro.observe(wrap)
      if (orq) ro.observe(orq)
      if (fe) ro.observe(fe)
      if (be) ro.observe(be)
    }

    const fontsReady = document.fonts?.ready?.then(layout)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', layout)
      ro?.disconnect()
      void fontsReady
    }
  }, [layout, wrapRef, orqRef, feRef, beRef])

  return (
    <svg
      ref={svgRef}
      className="tree-svg"
      aria-hidden="true"
      preserveAspectRatio="xMinYMin meet"
    >
      <defs>
        <linearGradient id="gradFE" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--ws-orq)" />
          <stop offset="55%" stopColor="var(--ws-cream)" />
          <stop offset="100%" stopColor="var(--ws-fe)" />
        </linearGradient>
        <linearGradient id="gradBE" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--ws-orq)" />
          <stop offset="55%" stopColor="var(--ws-cream)" />
          <stop offset="100%" stopColor="var(--ws-be)" />
        </linearGradient>
        <path ref={pathFeRef} id="pathFE" d="" />
        <path ref={pathBeRef} id="pathBE" d="" />
      </defs>
      <use href="#pathFE" className="line-fe-soft" />
      <use href="#pathBE" className="line-be-soft" />
      <use
        href="#pathFE"
        className={`line-fe glow${reduced ? ' is-static' : ''}`}
      />
      <use
        href="#pathBE"
        className={`line-be glow${reduced ? ' is-static' : ''}`}
      />
      {!reduced && (
        <>
          <circle className="particle" r="3.5" fill="var(--ws-cream)">
            <animateMotion dur="1.8s" repeatCount="indefinite" rotate="auto">
              <mpath href="#pathFE" />
            </animateMotion>
          </circle>
          <circle className="particle" r="2.4" fill="var(--ws-fe)">
            <animateMotion dur="1.8s" begin="0.6s" repeatCount="indefinite">
              <mpath href="#pathFE" />
            </animateMotion>
          </circle>
          <circle className="particle" r="3.5" fill="var(--ws-cream)">
            <animateMotion dur="2s" repeatCount="indefinite">
              <mpath href="#pathBE" />
            </animateMotion>
          </circle>
          <circle className="particle" r="2.4" fill="var(--ws-be)">
            <animateMotion dur="2s" begin="0.7s" repeatCount="indefinite">
              <mpath href="#pathBE" />
            </animateMotion>
          </circle>
        </>
      )}
    </svg>
  )
}
