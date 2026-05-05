/**
 * Mock Karnataka Single Window System (SWS) Portal
 * Simulates the government's business registration front-end.
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import './portal.css'

const API_BASE = import.meta.env.VITE_API_URL || ''
const UBIDS = Array.from({ length: 20 }, (_, i) => `KA-TEST-${String(i + 1).padStart(4, '0')}`)

export default function PortalSWS() {
  const [selectedUbid, setSelectedUbid] = useState('KA-TEST-0001')
  const [record, setRecord] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({})
  const [toast, setToast] = useState(null)
  const [activity, setActivity] = useState([])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4000)
  }

  const fetchRecord = useCallback(async (ubid) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/mock/sws/record/${ubid}`)
      if (!res.ok) throw new Error('Not found')
      const data = await res.json()
      setRecord(data)
      setForm({
        registered_address: data.registered_address || '',
        authorized_signatory: data.authorized_signatory || '',
        primary_contact: data.primary_contact || '',
        employee_headcount: data.employee_headcount || 0,
        operational_status: data.operational_status || 'active',
        license_status: data.license_status || 'valid',
      })
    } catch {
      setRecord(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRecord(selectedUbid) }, [selectedUbid, fetchRecord])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await fetch(`${API_BASE}/api/mock/sws/record/${selectedUbid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error('Update failed')
      const data = await res.json()
      const updated = data.updated_fields || []
      showToast(`✅ Record updated successfully. Fields changed: ${updated.join(', ') || 'none'}`)
      setActivity(a => [{
        time: new Date().toLocaleTimeString(),
        ubid: selectedUbid,
        fields: updated.join(', ') || '—',
        user: 'Officer Ramesh K.',
      }, ...a.slice(0, 9)])
      await fetchRecord(selectedUbid)
    } catch (err) {
      showToast(`❌ Update failed: ${err.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="portal-root portal-sws">
      {/* Government Header */}
      <header className="portal-header">
        <div className="portal-header-inner">
          <div className="portal-emblem">
            <div className="portal-emblem-circle">🏛️</div>
            <div>
              <div className="portal-gov-name">Government of Karnataka</div>
              <div className="portal-dept-name">Single Window System — Business Registration Portal</div>
            </div>
          </div>
          <div className="portal-header-right">
            <span className="portal-user">👤 Officer Ramesh K. | SWS Admin</span>
            <div className="portal-nav-links">
              <Link to="/portal/shop" className="portal-nav-link">🏪 Shop Est. Portal</Link>
              <Link to="/portal/factories" className="portal-nav-link">🏭 Factories Portal</Link>
              <Link to="/" className="portal-nav-link portal-nav-link-dashboard">📊 SyncKar Dashboard</Link>
            </div>
          </div>
        </div>
        <div className="portal-breadcrumb">
          Home &rsaquo; Business Services &rsaquo; Update Business Record
        </div>
      </header>

      {toast && <div className={`portal-toast portal-toast-${toast.type}`}>{toast.msg}</div>}

      <main className="portal-main">
        <div className="portal-page-title">
          <h1>Update Business Record</h1>
          <p>Modify registered business details. Changes will be automatically synchronized to all connected department systems via SyncKar.</p>
        </div>

        <div className="portal-layout">
          {/* Left: Form */}
          <div className="portal-form-section">
            <div className="portal-card">
              <div className="portal-card-header sws-header">
                <span>📋 Business Details — SWS Record</span>
                <select
                  className="portal-ubid-select"
                  value={selectedUbid}
                  onChange={e => setSelectedUbid(e.target.value)}
                >
                  {UBIDS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>

              {loading ? (
                <div className="portal-loading">
                  <div className="portal-spinner" />
                  Loading record…
                </div>
              ) : !record ? (
                <div className="portal-empty">Record not found for {selectedUbid}</div>
              ) : (
                <form onSubmit={handleSubmit} className="portal-form">
                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>UBID (Unique Business Identifier)</label>
                      <input type="text" value={selectedUbid} disabled className="portal-input portal-input-disabled" />
                    </div>
                    <div className="portal-field">
                      <label>Business Name</label>
                      <input type="text" value={record.business_name || ''} disabled className="portal-input portal-input-disabled" />
                    </div>
                  </div>

                  <div className="portal-field">
                    <label>Registered Address <span className="portal-required">*</span></label>
                    <input
                      type="text"
                      className="portal-input"
                      value={form.registered_address}
                      onChange={e => setForm(f => ({ ...f, registered_address: e.target.value }))}
                      placeholder="Enter registered address"
                    />
                    <span className="portal-hint">This field is authoritative in SWS (SWS_WINS policy)</span>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Authorized Signatory <span className="portal-required">*</span></label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.authorized_signatory}
                        onChange={e => setForm(f => ({ ...f, authorized_signatory: e.target.value }))}
                      />
                    </div>
                    <div className="portal-field">
                      <label>Primary Contact</label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.primary_contact}
                        onChange={e => setForm(f => ({ ...f, primary_contact: e.target.value }))}
                      />
                    </div>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Employee Headcount</label>
                      <input
                        type="number"
                        className="portal-input"
                        value={form.employee_headcount}
                        onChange={e => setForm(f => ({ ...f, employee_headcount: Number(e.target.value) }))}
                        min={0}
                      />
                    </div>
                    <div className="portal-field">
                      <label>Operational Status</label>
                      <select
                        className="portal-input"
                        value={form.operational_status}
                        onChange={e => setForm(f => ({ ...f, operational_status: e.target.value }))}
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>
                    <div className="portal-field">
                      <label>License Status</label>
                      <select
                        className="portal-input"
                        value={form.license_status}
                        onChange={e => setForm(f => ({ ...f, license_status: e.target.value }))}
                      >
                        <option value="valid">Valid</option>
                        <option value="expired">Expired</option>
                        <option value="revoked">Revoked</option>
                      </select>
                    </div>
                  </div>

                  <div className="portal-form-footer">
                    <div className="portal-sync-note">
                      🔄 SyncKar will detect this change within ~5 seconds and propagate it to Shop Establishment and Factories departments automatically.
                    </div>
                    <button type="submit" className="portal-btn portal-btn-primary" disabled={saving}>
                      {saving ? '⏳ Submitting…' : '✅ Submit Update'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Right: Current state + activity */}
          <div className="portal-sidebar">
            <div className="portal-card">
              <div className="portal-card-header sws-header">📊 Current Record State</div>
              {record && (
                <div className="portal-record-view">
                  {[
                    ['UBID', selectedUbid],
                    ['Business Name', record.business_name],
                    ['Address', record.registered_address],
                    ['Signatory', record.authorized_signatory],
                    ['Contact', record.primary_contact],
                    ['Employees', record.employee_headcount],
                    ['Status', record.operational_status],
                    ['License', record.license_status],
                    ['Last Modified', record.last_modified?.slice(0, 19)],
                  ].map(([k, v]) => (
                    <div key={k} className="portal-record-row">
                      <span className="portal-record-key">{k}</span>
                      <span className="portal-record-val">{v || '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="portal-card">
              <div className="portal-card-header sws-header">📝 Recent Activity</div>
              {activity.length === 0 ? (
                <div className="portal-empty-sm">No updates yet this session</div>
              ) : (
                <div className="portal-activity">
                  {activity.map((a, i) => (
                    <div key={i} className="portal-activity-row">
                      <span className="portal-activity-time">{a.time}</span>
                      <span className="portal-activity-ubid">{a.ubid}</span>
                      <span className="portal-activity-fields">{a.fields}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      <footer className="portal-footer">
        <div>© 2024 Government of Karnataka — Department of Commerce & Industries</div>
        <div>Powered by SyncKar Interoperability Layer | BSA 2023 Compliant</div>
      </footer>
    </div>
  )
}
