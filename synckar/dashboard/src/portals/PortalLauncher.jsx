/**
 * Portal Launcher — entry page showing all three department portals
 */
import { Link } from 'react-router-dom'
import './portal.css'

export default function PortalLauncher() {
  return (
    <div className="portal-launcher-root">
      <div className="portal-launcher">
        <div className="portal-launcher-header">
          <div className="portal-launcher-emblem">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h1>Government of Karnataka Portals</h1>
          <p className="portal-launcher-sub">
            SyncKar Interoperability Demo Environment
          </p>
        </div>

        <div className="portal-launcher-cards">
          <Link to="/portal/sws" className="portal-launcher-card portal-launcher-card-sws">
            <div className="portal-launcher-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect width="18" height="18" x="3" y="3" rx="2" ry="2"></rect>
              </svg>
            </div>
            <div className="portal-launcher-name">Single Window System</div>
            <div className="portal-launcher-desc">Business Registration & Services. Primary authority for demographic data.</div>
            <div className="portal-launcher-tag">Primary Authority</div>
          </Link>

          <Link to="/portal/shop" className="portal-launcher-card portal-launcher-card-shop">
            <div className="portal-launcher-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
              </svg>
            </div>
            <div className="portal-launcher-name">Shop Establishment</div>
            <div className="portal-launcher-desc">Department of Labour. Mock environment for shop registrations.</div>
            <div className="portal-launcher-tag">Department Portal</div>
          </Link>

          <Link to="/portal/factories" className="portal-launcher-card portal-launcher-card-factories">
            <div className="portal-launcher-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 20h20M4 20V4l8 6 8-6v16"></path>
              </svg>
            </div>
            <div className="portal-launcher-name">Factories Department</div>
            <div className="portal-launcher-desc">Dept. of Factories & Boilers. Mock environment for compliance records.</div>
            <div className="portal-launcher-tag">Department Portal</div>
          </Link>
        </div>

        <div className="portal-synckar-note">
          <div className="portal-synckar-text">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--gov-primary)" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            <strong>SyncKar Active:</strong> Changes made in any portal are automatically propagated.
          </div>
          <Link to="/">Open Dashboard</Link>
        </div>
      </div>
    </div>
  )
}
