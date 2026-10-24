import { Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { DesignPage } from './pages/DesignPage'
import { HomePage } from './pages/HomePage'
import { DeliveryReturnsPage, PrivacyPage, TermsPage } from './pages/legal'
import { NotFoundPage } from './pages/NotFoundPage'
import { ProductPage } from './pages/ProductPage'
import { ShopPage } from './pages/ShopPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="sklep" element={<ShopPage />} />
        <Route path="sklep/:slug" element={<ProductPage />} />
        <Route path="regulamin" element={<TermsPage />} />
        <Route path="polityka-prywatnosci" element={<PrivacyPage />} />
        <Route path="dostawa-i-zwroty" element={<DeliveryReturnsPage />} />
        <Route path="design" element={<DesignPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
