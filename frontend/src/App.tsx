import { Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { DesignPage } from './pages/DesignPage'
import { HomePage } from './pages/HomePage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="design" element={<DesignPage />} />
      </Route>
    </Routes>
  )
}
