import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import PortalSWS from './portals/PortalSWS.jsx'
import PortalShop from './portals/PortalShop.jsx'
import PortalFactories from './portals/PortalFactories.jsx'
import PortalLauncher from './portals/PortalLauncher.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter basename="/dashboard">
      <Routes>
        {/* Main SyncKar dashboard */}
        <Route path="/" element={<App />} />

        {/* Government department portals */}
        <Route path="/portal" element={<PortalLauncher />} />
        <Route path="/portal/sws" element={<PortalSWS />} />
        <Route path="/portal/shop" element={<PortalShop />} />
        <Route path="/portal/factories" element={<PortalFactories />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
