import spriteSvg from '../assets/brand-sprite.svg?raw'

// Rendered once in the layout, so illustrations can reference #pm-pot, #pm-mark etc. via <use>.
export function BrandSprite() {
  return <div hidden dangerouslySetInnerHTML={{ __html: spriteSvg }} />
}
