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
          <div className="portal-launcher-emblem">🏛️</div>
          <h1>Karnataka Government — Department Portals</h1>
          <p className="portal-launcher-sub">
            Demo environment for SyncKar interoperability prototype · Make changes in any portal and watch SyncKar propagate them in real time
          </p>
        </div>

        <div className="portal-launcher-cards">
          <Link to="/portal/sws" className="portal-launcher-card portal-launcher-card-sws">
            <div className="portal-launcher-icon">🏛️</div>
            <div className="portal-launcher-name">Single Window System</div>
            <div className="portal-launcher-desc">Karnataka SWS — Business Registration &amp; Services. Primary authority for demographic data.</div>
            <div className="portal-launcher-tag">Primary Authority</div>
          </Link>

          <Link to="/portal/shop" className="portal-launcher-card portal-launcher-card-shop">
            <div className="portal-launcher-icon">🏪</div>
            <div className="portal-launcher-name">Shop Establishment Dept.</div>
            <div className="portal-launcher-desc">Department of Labour — Shop &amp; Establishment Registrations. 18 businesses registered.</div>
            <div className="portal-launcher-tag">Department Portal</div>
          </Link>

          <Link to="/portal/factories" className="portal-launcher-card portal-launcher-card-factories">
            <div className="portal-launcher-icon">🏭</div>
            <div className="portal-launcher-name">Factories Department</div>
            <div className="portal-launcher-desc">Dept. of Factories, Boilers, Industrial Safety &amp; Health. 15 factories registered.</div>
            <div className="portal-launcher-tag">Department Portal</div>
          </Link>
        </div>

        <div className="portal-synckar-note">
          <span className="portal-synckar-badge">⚡ SyncKar Active</span>
          Changes made in any portal are automatically detected and propagated by the SyncKar middleware within ~5–10 seconds.
          <Link to="/">Open SyncKar Dashboard →</Link>
        </div>
      </div>
    </div>
  )
}
