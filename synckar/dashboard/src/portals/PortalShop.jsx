/**
 * Mock Shop Establishment Department Portal
 * Simulates the department's internal record management system.
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import './portal.css'

const API_BASE = import.meta.env.VITE_API_URL || ''
const UBIDS = Array.from({ length: 18 }, (_, i) => `KA-TEST-${String(i + 1).padStart(4, '0')}`)

export default function PortalShop() {
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
      const res = await fetch(`${API_BASE}/api/mock/shop/record/${ubid}`)
      if (!res.ok) throw new Error('Not found')
      const data = await res.json()
      setRecord(data)
      setForm({
        Buss_Addr_Line1: data.Buss_Addr_Line1 || '',
        Auth_Sign_Name: data.Auth_Sign_Name || '',
        Contact_Phone: data.Contact_Phone || '',
        Emp_Count: data.Emp_Count || 0,
        Op_Status: data.Op_Status || 'active',
        Lic_Status: data.Lic_Status || 'valid',
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
      const res = await fetch(`${API_BASE}/api/mock/shop/record/${selectedUbid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error('Update failed')
      const data = await res.json()
      const updated = data.updated_fields || []
      showToast(`✅ Record updated. Fields changed: ${updated.join(', ') || 'none'}`)
      setActivity(a => [{
        time: new Date().toLocaleTimeString(),
        ubid: selectedUbid,
        fields: updated.join(', ') || '—',
        user: 'Inspector Priya M.',
      }, ...a.slice(0, 9)])
      await fetchRecord(selectedUbid)
    } catch (err) {
      showToast(`❌ Update failed: ${err.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="portal-root portal-shop">
      <header className="portal-header">
        <div className="portal-header-inner">
          <div className="portal-emblem">
            <div className="portal-emblem-circle shop-emblem">🏪</div>
            <div>
              <div className="portal-gov-name">Government of Karnataka</div>
              <div className="portal-dept-name">Department of Shop & Commercial Establishment — Record Management System</div>
            </div>
          </div>
          <div className="portal-header-right">
            <span className="portal-user">👤 Inspector Priya M. | Shop Est. Dept.</span>
            <div className="portal-nav-links">
              <Link to="/portal/sws" className="portal-nav-link">🏛️ SWS Portal</Link>
              <Link to="/portal/factories" className="portal-nav-link">🏭 Factories Portal</Link>
              <Link to="/" className="portal-nav-link portal-nav-link-dashboard">📊 SyncKar Dashboard</Link>
            </div>
          </div>
        </div>
        <div className="portal-breadcrumb">
          Home &rsaquo; Establishment Records &rsaquo; Update Record
        </div>
      </header>

      {toast && <div className={`portal-toast portal-toast-${toast.type}`}>{toast.msg}</div>}

      <main className="portal-main">
        <div className="portal-page-title shop-title">
          <h1>Update Establishment Record</h1>
          <p>Modify shop establishment details. Note: Address changes made here may conflict with SWS records — SyncKar will apply the <strong>SWS_WINS</strong> policy for address fields.</p>
        </div>

        <div className="portal-layout">
          <div className="portal-form-section">
            <div className="portal-card">
              <div className="portal-card-header shop-header">
                <span>📋 Establishment Record — Shop Est. Dept.</span>
                <select
                  className="portal-ubid-select"
                  value={selectedUbid}
                  onChange={e => setSelectedUbid(e.target.value)}
                >
                  {UBIDS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>

              {loading ? (
                <div className="portal-loading"><div className="portal-spinner shop-spinner" />Loading record…</div>
              ) : !record ? (
                <div className="portal-empty">Record not found for {selectedUbid} in Shop Establishment</div>
              ) : (
                <form onSubmit={handleSubmit} className="portal-form">
                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>UBID</label>
                      <input type="text" value={selectedUbid} disabled className="portal-input portal-input-disabled" />
                    </div>
                    <div className="portal-field">
                      <label>Shop Reg. No.</label>
                      <input type="text" value={record.shop_reg_no || ''} disabled className="portal-input portal-input-disabled" />
                    </div>
                  </div>

                  <div className="portal-field">
                    <label>Business Name</label>
                    <input type="text" value={record.business_name || ''} disabled className="portal-input portal-input-disabled" />
                  </div>

                  <div className="portal-field">
                    <label>Business Address (Buss_Addr_Line1) <span className="portal-required">*</span></label>
                    <input
                      type="text"
                      className="portal-input"
                      value={form.Buss_Addr_Line1}
                      onChange={e => setForm(f => ({ ...f, Buss_Addr_Line1: e.target.value }))}
                    />
                    <span className="portal-hint">⚠️ If SWS has a different address, SWS_WINS policy will override this value</span>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Auth. Signatory (Auth_Sign_Name)</label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.Auth_Sign_Name}
                        onChange={e => setForm(f => ({ ...f, Auth_Sign_Name: e.target.value }))}
                      />
                    </div>
                    <div className="portal-field">
                      <label>Contact Phone</label>
                      <input
                        type="text"
                        className="portal-input"
                        value={form.Contact_Phone}
                        onChange={e => setForm(f => ({ ...f, Contact_Phone: e.target.value }))}
                      />
                    </div>
                  </div>

                  <div className="portal-form-row">
                    <div className="portal-field">
                      <label>Employee Count (Emp_Count)</label>
                      <input
                        type="number"
                        className="portal-input"
                        value={form.Emp_Count}
                        onChange={e => setForm(f => ({ ...f, Emp_Count: Number(e.target.value) }))}
                        min={0}
                      />
                    </div>
                    <div className="portal-field">
                      <label>Operational Status (Op_Status)</label>
                      <select
                        className="portal-input"
                        value={form.Op_Status}
                        onChange={e => setForm(f => ({ ...f, Op_Status: e.target.value }))}
                      >
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>
                    <div className="portal-field">
                      <label>License Status (Lic_Status)</label>
                      <select
                        className="portal-input"
                        value={form.Lic_Status}
                        onChange={e => setForm(f => ({ ...f, Lic_Status: e.target.value }))}
                      >
                        <option value="valid">Valid</option>
                        <option value="expired">Expired</option>
                        <option value="revoked">Revoked</option>
                      </select>
                    </div>
                  </div>

                  <div className="portal-form-footer">
                    <div className="portal-sync-note shop-sync-note">
                      🔄 SyncKar polls this system every 10 seconds. Changes will be detected and propagated to SWS automatically.
                    </div>
                    <button type="submit" className="portal-btn portal-btn-shop" disabled={saving}>
                      {saving ? '⏳ Submitting…' : '✅ Submit Update'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          <div className="portal-sidebar">
            <div className="portal-card">
              <div className="portal-card-header shop-header">📊 Current Record State</div>
              {record && (
                <div className="portal-record-view">
                  {[
                    ['UBID', selectedUbid],
                    ['Shop Reg No', record.shop_reg_no],
                    ['Business Name', record.business_name],
                    ['Address', record.Buss_Addr_Line1],
                    ['Signatory', record.Auth_Sign_Name],
                    ['Phone', record.Contact_Phone],
                    ['Employees', record.Emp_Count],
                    ['Op Status', record.Op_Status],
                    ['Lic Status', record.Lic_Status],
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
              <div className="portal-card-header shop-header">📝 Recent Activity</div>
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

      <footer className="portal-footer shop-footer">
        <div>© 2024 Government of Karnataka — Department of Shop & Commercial Establishment</div>
        <div>Powered by SyncKar Interoperability Layer | BSA 2023 Compliant</div>
      </footer>
    </div>
  )
}
