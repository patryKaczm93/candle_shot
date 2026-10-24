type IllustrationProps = {
  /** Raw SVG markup imported with `?raw` from src/assets/illustrations. */
  svg: string
  className?: string
}

// Mockup illustrations kept as SVG files, so their shapes stay identical to the design.
export function Illustration({ svg, className }: IllustrationProps) {
  return <span className={className} dangerouslySetInnerHTML={{ __html: svg }} />
}
