/**
 * Mock Factories Department Portal
 * Simulates the department's internal factory record management system.
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import './portal.css'

const API_BASE = import.meta.env.VITE_API_URL || ''
const UBIDS = Array.from({ length: 15 }, (_, i) => `KA-TEST-${String(i + 1).padStart(4, '0')}`)

export default function PortalFactories() {
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
      const res = await fetch(`${API_BASE}/api/mock/factories/record/${ubid}`)
      if (!res.ok) throw new Error('Not found')
      const data = await res.json()
      setRecord(data)
      setForm({
        factory_address: data.factory_address || '',
        signatory_name: data.signatory_name || '',
        contact_number: data.contact_number || '',
        worker_count: data.worker_count || 0,
        factory_status: data.factory_status || 'active',
        lic_status: data.lic_status || 'valid',
        safety_cert: data.safety_cert || 'approved',
        labor_violations: data.labor_violations || 'none',
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
      const res = await fetch(`${API_BASE}/api/mock/factories/record/${selectedUbid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error('Update failed')
      const data = await res.json()
      const updated = data.updated_fields || []
      showToast(`✅ Factory record updated. Fields changed: ${updated.join(', ') || 'none'}`)
      setActivity(a => [{
        time: new Date().toLocaleTimeString(),
        ubid: selectedUbid,
        fields: updated.join(', ') || '—',
        user: 'Inspector Suresh B.',
      }, ...a.slice(0, 9)])
      await fetchRecord(selectedUbid)
    } catch (err) {
      showToast(`❌ Update failed: ${err.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="portal-root portal-factories">
      <header className="portal-header factories-header">
        <div className="portal-header-inner">
          <div className="portal-emblem">
            <div className="portal-emblem-circle factories-emblem">🏭</div>
            <div>
              <div className="portal-gov-name">Government of Karnataka</div>
              <div className="portal-dept-name">Department of Factories, Boilers, Industrial Safety & Health — Record System</div>
            </div>
          </div>
          <div className="portal-header-right">
            <span className="portal-user">👤 Inspector Suresh B. | Factories Dept.</span>
            <div className="portal-nav-links">
              <Link to="/portal/sws" className="portal-nav-link">🏛️ SWS Portal</Link>
              <Link to="/portal/shop" className="portal-nav-link">🏪 Shop Est. Portal</Link>
              <Link to="/" className="portal-nav-link portal-nav-link-dashboard">📊 SyncKar Dashboard</Link>
            </div>
          </div>
        </div>
        <div className="portal-breadcrumb">
          Home &rsaquo; Factory Records &rsaquo; Update Factory Record
        </div>
      </header>

      {toast && <div className={`portal-toast portal-toast-${toast.type}`}>{toast.msg}</div>}

      <main className="portal-main">
        <div className="portal-page-title factories-title">
          <h1>Update Factory Record</h1>
          <p>Modify factory registration details. Compliance fields (license status, safety cert, labor violations) are <strong>authoritative in this department</strong> — SyncKar applies DEPT_WINS policy for these fields.</p>
        </div>

        <div className="portal-layout">
          <div className="portal-form-section">
            <div className="portal-card">
              <div className="portal-card-header factories-header-card">
                <span>📋 Factory Record — Factories Dept.</span>
                <select
                  className="portal-ubid-select"
                  value={selectedUbid}
                  onChange={e => setSelectedUbid(e.target.value)}
                >
                  {UBIDS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>

              {loading ? (
                <div className="portal-loading"><div className="portal-spinner factories-spinner" />Loading record…</div>
              ) : !record ? (
                <div className="portal-empty">Record not found for {selectedUbid} in Factories Dept.</div>
              ) : (
                <form onSubmit={handleSubmit} className="portal-form">
                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>UBID</label>
                      <input type="text" value={selectedUbid} disabled className="portal-input portal-input-disabled" />
                    </div>
                    <div className="portal-field">
                      <label>Factory License No.</label>
                      <input type="text" value={record.factory_license_no || ''} disabled className="portal-input portal-input-disabled" />
                    </div>
                  </div>

                  <div className="portal-field">
                    <label>Business Name</label>
                    <input type="text" value={record.business_name || ''} disabled className="portal-input portal-input-disabled" />
                  </div>

                  <div className="portal-field">
                    <label>Factory Address <span className="portal-required">*</span></label>
                    <input
                      type="text"
                      className="portal-input"
                      value={form.factory_address}
                      onChange={e => setForm(f => ({ ...f, factory_address: e.target.value }))}
                    />
                    <span className="portal-hint">⚠️ Address conflicts with SWS will be resolved by SWS_WINS policy</span>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Signatory Name</label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.signatory_name}
                        onChange={e => setForm(f => ({ ...f, signatory_name: e.target.value }))}
                      />
                      <span className="portal-hint">Changes here propagate to SWS</span>
                    </div>
                    <div className="portal-field">
                      <label>Contact Number</label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.contact_number}
                        onChange={e => setForm(f => ({ ...f, contact_number: e.target.value }))}
                      />
                    </div>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Worker Count</label>
                      <input
                        type="number"
                        className="portal-input"
                        value={form.worker_count}
                        onChange={e => setForm(f => ({ ...f, worker_count: Number(e.target.value) }))}
                        min={0}
                      />
                    </div>
                    <div className="portal-field">
                      <label>Factory Status</label>
                      <select
                        className="portal-input"
                        value={form.factory_status}
                        onChange={e => setForm(f => ({ ...f, factory_status: e.target.value }))}
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>
                  </div>

                  <div className="portal-section-label">🔒 Compliance Fields (DEPT_WINS — Factories is authoritative)</div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>License Status</label>
                      <select
                        className="portal-input portal-input-compliance"
                        value={form.lic_status}
                        onChange={e => setForm(f => ({ ...f, lic_status: e.target.value }))}
                      >
                        <option value="valid">Valid</option>
                        <option value="expired">Expired</option>
                        <option value="revoked">Revoked</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>
                    <div className="portal-field">
                      <label>Safety Certificate</label>
                      <select
                        className="portal-input portal-input-compliance"
                        value={form.safety_cert}
                        onChange={e => setForm(f => ({ ...f, safety_cert: e.target.value }))}
                      >
                        <option value="approved">Approved</option>
                        <option value="pending">Pending</option>
                        <option value="rejected">Rejected</option>
                        <option value="expired">Expired</option>
                      </select>
                    </div>
                    <div className="portal-field">
                      <label>Labor Violations</label>
                      <select
                        className="portal-input portal-input-compliance"
                        value={form.labor_violations}
                        onChange={e => setForm(f => ({ ...f, labor_violations: e.target.value }))}
                      >
                        <option value="none">None</option>
                        <option value="minor">Minor</option>
                        <option value="major">Major</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>
                  </div>

                  <div className="portal-form-footer">
                    <div className="portal-sync-note factories-sync-note">
                      🔄 SyncKar polls this system every 10 seconds. Signatory changes will propagate to SWS. Compliance fields (license, safety, labor) are authoritative here.
                    </div>
                    <button type="submit" className="portal-btn portal-btn-factories" disabled={saving}>
                      {saving ? '⏳ Submitting…' : '✅ Submit Update'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          <div className="portal-sidebar">
            <div className="portal-card">
              <div className="portal-card-header factories-header-card">📊 Current Record State</div>
              {record && (
                <div className="portal-record-view">
                  {[
                    ['UBID', selectedUbid],
                    ['License No', record.factory_license_no],
                    ['Business Name', record.business_name],
                    ['Address', record.factory_address],
                    ['Signatory', record.signatory_name],
                    ['Contact', record.contact_number],
                    ['Workers', record.worker_count],
                    ['Status', record.factory_status],
                    ['License', record.lic_status],
                    ['Safety Cert', record.safety_cert],
                    ['Labor', record.labor_violations],
                    ['Last Modified', record.last_modified?.slice(0, 19)],
                  ].map(([k, v]) => (
                    <div key={k} className="portal-record-row">
                      <span className="portal-record-key">{k}</span>
                      <span className="portal-record-val">{v ?? '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="portal-card">
              <div className="portal-card-header factories-header-card">📝 Recent Activity</div>
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

      <footer className="portal-footer factories-footer">
        <div>© 2024 Government of Karnataka — Dept. of Factories, Boilers, Industrial Safety & Health</div>
        <div>Powered by SyncKar Interoperability Layer | BSA 2023 Compliant</div>
      </footer>
    </div>
  )
}
