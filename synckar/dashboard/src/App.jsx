import { useState, useEffect, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import './index.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

// All 20 UBIDs with business names
const UBID_LIST = [
  { ubid: 'KA-TEST-0001', name: 'Bengaluru Silk Weavers Pvt Ltd' },
  { ubid: 'KA-TEST-0002', name: 'Mysuru Agro Industries Ltd' },
  { ubid: 'KA-TEST-0003', name: 'Hubli Steel Fabricators Pvt Ltd' },
  { ubid: 'KA-TEST-0004', name: 'Mangaluru Cashew Exports Ltd' },
  { ubid: 'KA-TEST-0005', name: 'Dharwad Pharma Solutions Pvt Ltd' },
  { ubid: 'KA-TEST-0006', name: 'Belagavi Textile Mills Ltd' },
  { ubid: 'KA-TEST-0007', name: 'Tumkur Auto Components Pvt Ltd' },
  { ubid: 'KA-TEST-0008', name: 'Shivamogga Paper Industries Ltd' },
  { ubid: 'KA-TEST-0009', name: 'Kolar Gold Jewellers Pvt Ltd' },
  { ubid: 'KA-TEST-0010', name: 'Raichur Power Equipment Ltd' },
  { ubid: 'KA-TEST-0011', name: 'Bidar Ceramics Pvt Ltd' },
  { ubid: 'KA-TEST-0012', name: 'Vijayapura Sugar Mills Ltd' },
  { ubid: 'KA-TEST-0013', name: 'Gadag Granite Exports Pvt Ltd' },
  { ubid: 'KA-TEST-0014', name: 'Koppal Iron & Steel Ltd' },
  { ubid: 'KA-TEST-0015', name: 'Yadgir Cement Works Pvt Ltd' },
  { ubid: 'KA-TEST-0016', name: 'Bengaluru IT Solutions Pvt Ltd' },
  { ubid: 'KA-TEST-0017', name: 'Mysuru Handicrafts Emporium' },
  { ubid: 'KA-TEST-0018', name: 'Mangaluru Seafood Processors Ltd' },
  { ubid: 'KA-TEST-0019', name: 'Bengaluru Fintech Ventures Pvt Ltd' },
  { ubid: 'KA-TEST-0020', name: 'Karnataka Organic Farms Ltd' },
]

function App() {
  const [page, setPage] = useState('overview')
  const [stats, setStats] = useState(null)
  const [audit, setAudit] = useState([])
  const [conflicts, setConflicts] = useState([])
  const [dlq, setDlq] = useState([])
  const [searchUbid, setSearchUbid] = useState('')
  const [verifyResult, setVerifyResult] = useState(null)
  const [health, setHealth] = useState(null)

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`)
      const data = await res.json()
      setStats(data)
    } catch (e) { console.error('Stats fetch failed:', e) }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      const data = await res.json()
      setHealth(data)
    } catch (e) { console.error('Health fetch failed:', e) }
  }, [])

  const fetchAudit = useCallback(async (ubid = '') => {
    try {
      const params = ubid ? `?ubid=${ubid}` : '?limit=50'
      const res = await fetch(`${API_BASE}/api/audit${params}`)
      const data = await res.json()
      setAudit(data.audit_entries || [])
    } catch (e) { console.error('Audit fetch failed:', e) }
  }, [])

  const fetchConflicts = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dlq/conflicts`)
      const data = await res.json()
      setConflicts(data.conflicts || [])
    } catch (e) { console.error('Conflicts fetch failed:', e) }
  }, [])

  const fetchDlq = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dlq`)
      const data = await res.json()
      setDlq(data.dlq_items || [])
    } catch (e) { console.error('DLQ fetch failed:', e) }
  }, [])

  const verifyAudit = async (auditId) => {
    try {
      const res = await fetch(`${API_BASE}/api/audit/verify/${auditId}`)
      const data = await res.json()
      setVerifyResult(data)
    } catch (e) { console.error('Verify failed:', e) }
  }

  // Auto-refresh stats
  useEffect(() => {
    fetchStats()
    fetchHealth()
    const interval = setInterval(() => {
      fetchStats()
      fetchHealth()
    }, 3000)
    return () => clearInterval(interval)
  }, [fetchStats, fetchHealth])

  useEffect(() => {
    if (page === 'audit') fetchAudit(searchUbid)
    if (page === 'conflicts') fetchConflicts()
    if (page === 'dlq') fetchDlq()
  }, [page, fetchAudit, fetchConflicts, fetchDlq, searchUbid])

  // Auto-refresh audit/conflicts when on those pages
  useEffect(() => {
    if (page !== 'audit' && page !== 'conflicts') return
    const interval = setInterval(() => {
      if (page === 'audit') fetchAudit(searchUbid)
      if (page === 'conflicts') fetchConflicts()
    }, 4000)
    return () => clearInterval(interval)
  }, [page, fetchAudit, fetchConflicts, searchUbid])

  const pages = [
    { id: 'overview', label: 'Overview' },
    { id: 'mock', label: 'Data Flow Demo' },
    { id: 'audit', label: 'Audit Trail' },
    { id: 'conflicts', label: 'Conflicts' },
    { id: 'dlq', label: 'DLQ' },
    { id: 'verify', label: 'BSA Verify' }
  ]

  return (
    <div className="app">
      <header className="header">
        <div className="header-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
          <h1>SyncKar Dashboard</h1>
          <span className="badge-version">v1.2</span>
        </div>
        <nav className="nav">
          {pages.map(p => (
            <button
              key={p.id}
              className={`nav-btn ${page === p.id ? 'active' : ''}`}
              onClick={() => setPage(p.id)}
            >
              {p.label}
            </button>
          ))}
          <Link to="/portal" className="nav-btn-portals">
            Department Portals
          </Link>
        </nav>
      </header>

      <main className="main">
        {page === 'overview'  && <OverviewPage stats={stats} health={health} />}
        {page === 'mock'      && <MockSystemsPage />}
        {page === 'audit'     && (
          <AuditPage
            audit={audit}
            searchUbid={searchUbid}
            onSearch={setSearchUbid}
            onFetch={() => fetchAudit(searchUbid)}
          />
        )}
        {page === 'conflicts' && <ConflictsPage conflicts={conflicts} onRefresh={fetchConflicts} />}
        {page === 'dlq'       && <DLQPage dlq={dlq} />}
        {page === 'verify'    && (
          <VerifyPage
            audit={audit}
            verifyResult={verifyResult}
            onVerify={verifyAudit}
            onFetchAudit={() => fetchAudit('')}
          />
        )}
      </main>
    </div>
  )
}

// ─── Overview ────────────────────────────────────────────────────────────────

function OverviewPage({ stats, health }) {
  return (
    <>
      <div className="page-title">
        <h2>System Overview</h2>
        <p>Real-time metrics for the SyncKar Interoperability Layer</p>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Propagations</div>
          <div className="stat-value">{stats?.audit_entries ?? '—'}</div>
        </div>
        <div className="stat-card amber">
          <div className="stat-label">Conflicts Detected</div>
          <div className="stat-value">{stats?.conflicts_detected ?? '—'}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">DLQ Depth</div>
          <div className="stat-value">{stats?.dlq_depth ?? '—'}</div>
        </div>
        <div className="stat-card purple">
          <div className="stat-label">Outbox Pending</div>
          <div className="stat-value">{stats?.outbox_pending ?? '—'}</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3>Service Health</h3>
          <span className={`badge ${health?.status === 'healthy' ? 'badge-success' : 'badge-error'}`}>
            {health?.status === 'healthy' ? 'Operational' : 'Degraded'}
          </span>
        </div>
        <table>
          <thead>
            <tr><th>Service Node</th><th>Status</th></tr>
          </thead>
          <tbody>
            {health?.checks && Object.entries(health.checks).map(([svc, status]) => (
              <tr key={svc}>
                <td className="mono">{svc}</td>
                <td>
                  <span className={`badge ${status === 'healthy' ? 'badge-success' : 'badge-error'}`}>
                    {status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ─── Mock Systems (Clean Pipeline View) ──────────────────────────────────────

function MockSystemsPage() {
  const [selectedUbid, setSelectedUbid] = useState('KA-TEST-0001')
  const [records, setRecords] = useState({ sws: null, shop: null, factories: null })
  const [saving, setSaving] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [edits, setEdits] = useState({})
  const [toast, setToast] = useState(null)
  const [syncActive, setSyncActive] = useState(false)
  const toastTimer = useRef(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 4000)
  }

  const triggerSyncAnimation = () => {
    setSyncActive(true)
    setTimeout(() => setSyncActive(false), 2000)
  }

  const fetchRecord = useCallback(async (system, ubid) => {
    try {
      const res = await fetch(`${API_BASE}/api/mock/${system}/record/${ubid}`)
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setRecords(r => ({ ...r, [system]: data }))
      // Pre-fill edits for SWS (Source of truth)
      if (system === 'sws') {
        setEdits({
          registered_address: data.registered_address || '',
          employee_headcount: data.employee_headcount || 0,
        })
      }
    } catch (err) {
      setRecords(r => ({ ...r, [system]: null }))
    }
  }, [])

  const refreshAll = useCallback((ubid) => {
    fetchRecord('sws', ubid)
    fetchRecord('shop', ubid)
    fetchRecord('factories', ubid)
  }, [fetchRecord])

  useEffect(() => {
    setRecords({ sws: null, shop: null, factories: null })
    setEdits({})
    refreshAll(selectedUbid)
  }, [selectedUbid, refreshAll])

  const handleEdit = (key, value) => {
    setEdits(e => ({ ...e, [key]: value }))
  }

  const handleSaveSWS = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API_BASE}/api/mock/sws/record/${selectedUbid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(edits),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      showToast('SWS Record Updated. SyncKar is routing the changes.', 'info')
      triggerSyncAnimation()
      
      // Refresh to see changes propagate
      setTimeout(() => refreshAll(selectedUbid), 1000)
    } catch (err) {
      showToast(`Update Failed: ${err.message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleConflict = async () => {
    const swsBody = { registered_address: `Conflict Addr A - ${new Date().getTime()}` }
    const factBody = { factory_address: `Conflict Addr B - ${new Date().getTime()}` }
    showToast('Triggering simultaneous conflict...', 'warning')

    const [swsRes, factRes] = await Promise.all([
      fetch(`${API_BASE}/api/mock/sws/record/${selectedUbid}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(swsBody),
      }),
      fetch(`${API_BASE}/api/mock/factories/record/${selectedUbid}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(factBody),
      }),
    ])

    if (!swsRes.ok || !factRes.ok) {
      showToast('Conflict trigger failed. Ensure DB is seeded.', 'error')
      return
    }

    triggerSyncAnimation()
    showToast('Conflict created. SWS_WINS policy applied.', 'success')
    setTimeout(() => refreshAll(selectedUbid), 1500)
  }

  const handleAction = async (endpoint, successMsg) => {
    setSeeding(true)
    try {
      const res = await fetch(`${API_BASE}/api/mock/${endpoint}`, { method: 'POST' })
      if (!res.ok) throw new Error(`${res.status}`)
      showToast(successMsg, 'success')
      refreshAll(selectedUbid)
    } catch (err) {
      showToast(`Action failed: ${err.message}`, 'error')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
      )}

      <div className="page-title">
        <h2>Data Flow Demonstration</h2>
        <p>Update the source system (SWS) and observe SyncKar propagate the changes to connected department systems.</p>
      </div>

      <div className="demo-controls-bar">
        <div className="demo-controls-group">
          <label className="form-label" style={{ marginBottom: 0 }}>Target Business Entity:</label>
          <select
            className="input"
            style={{ width: '300px' }}
            value={selectedUbid}
            onChange={e => setSelectedUbid(e.target.value)}
          >
            {UBID_LIST.map(u => (
              <option key={u.ubid} value={u.ubid}>{u.ubid} - {u.name}</option>
            ))}
          </select>
        </div>
        <div className="demo-controls-group">
          <button className="btn btn-outline btn-sm" onClick={() => handleAction('seed', 'Database Seeded')} disabled={seeding}>
            Seed Database
          </button>
          <button className="btn btn-outline btn-sm" onClick={() => handleAction('reset', 'Database Reset')} disabled={seeding}>
            Reset All
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleConflict}>
            Simulate Conflict
          </button>
        </div>
      </div>

      <div className="pipeline-container">
        {/* Source System */}
        <div className="pipeline-node">
          <div className="pipeline-node-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="18" height="18" x="3" y="3" rx="2" ry="2"></rect>
            </svg>
            <div>
              <div className="pipeline-node-title">Single Window System</div>
              <div className="pipeline-node-subtitle">Source of Truth (Write Access)</div>
            </div>
          </div>
          <div className="pipeline-node-body">
            {!records.sws ? (
              <div className="text-muted">Entity not found. Please Seed Database.</div>
            ) : (
              <>
                <div className="form-group">
                  <label className="form-label">Registered Address</label>
                  <input
                    type="text"
                    className="input"
                    value={edits.registered_address ?? ''}
                    onChange={e => handleEdit('registered_address', e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Employee Headcount</label>
                  <input
                    type="number"
                    className="input"
                    value={edits.employee_headcount ?? ''}
                    onChange={e => handleEdit('employee_headcount', Number(e.target.value))}
                  />
                </div>
                
                <div className="node-footer">
                  <span className="last-sync mono">Last Update: {records.sws.last_modified?.slice(11, 19)}</span>
                  <button className="btn btn-primary" onClick={handleSaveSWS} disabled={saving}>
                    {saving ? 'Saving...' : 'Update Record'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Middleware */}
        <div className="pipeline-middleware">
          <svg className="middleware-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          <div className="middleware-title">SyncKar</div>
          <div className="middleware-desc">Event Bus & Resolver</div>
          <div className={`middleware-pulse ${syncActive ? 'active' : ''}`}>
            ● SYNCING...
          </div>
        </div>

        {/* Target Systems */}
        <div className="pipeline-node">
          <div className="pipeline-node-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <div>
              <div className="pipeline-node-title">Department Systems</div>
              <div className="pipeline-node-subtitle">Downstream Subscribers (Read-Only Demo)</div>
            </div>
          </div>
          <div className="pipeline-node-body">
            {!records.shop ? (
              <div className="text-muted">Entity not found. Please Seed Database.</div>
            ) : (
              <>
                <div style={{ marginBottom: '24px' }}>
                  <div className="form-label" style={{ color: 'var(--gov-blue)' }}>Shop Establishment Dept</div>
                  <div className="card" style={{ padding: '16px', marginBottom: '0' }}>
                    <div className="form-group" style={{ marginBottom: '8px' }}>
                      <span className="text-sm text-muted">Business Address:</span>
                      <div className="mono" style={{ fontSize: '13px' }}>{records.shop.Buss_Addr_Line1}</div>
                    </div>
                    <div className="form-group" style={{ marginBottom: '0' }}>
                      <span className="text-sm text-muted">Employee Count:</span>
                      <div className="mono" style={{ fontSize: '13px' }}>{records.shop.Emp_Count}</div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="form-label" style={{ color: 'var(--gov-blue)' }}>Factories Department</div>
                  <div className="card" style={{ padding: '16px', marginBottom: '0' }}>
                    <div className="form-group" style={{ marginBottom: '8px' }}>
                      <span className="text-sm text-muted">Factory Address:</span>
                      <div className="mono" style={{ fontSize: '13px' }}>{records.factories?.factory_address || '—'}</div>
                    </div>
                    <div className="form-group" style={{ marginBottom: '0' }}>
                      <span className="text-sm text-muted">Worker Count:</span>
                      <div className="mono" style={{ fontSize: '13px' }}>{records.factories?.worker_count || '—'}</div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Audit ────────────────────────────────────────────────────────────────────

function AuditPage({ audit, searchUbid, onSearch, onFetch }) {
  return (
    <div>
      <div className="page-title">
        <h2>Audit Trail</h2>
        <p>Immutable ledger of all data propagations across systems.</p>
      </div>
      <div className="table-container">
        <div className="table-header">
          <h3>Recent Events ({audit.length})</h3>
          <div className="table-controls">
            <input
              className="search-input"
              placeholder="Search by Target ID (UBID)..."
              value={searchUbid}
              onChange={e => onSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onFetch()}
            />
            <button className="btn btn-outline" onClick={onFetch}>Search</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Target ID</th>
              <th>Property Modified</th>
              <th>Direction</th>
              <th>Payload Snippet</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {audit.map((row, i) => (
              <tr key={i}>
                <td className="mono">{row.created_at?.slice(0, 19).replace('T', ' ')}</td>
                <td><span className="badge badge-neutral">{row.ubid}</span></td>
                <td>{row.field_modified}</td>
                <td className="text-sm">
                  {row.source_system} &rarr; {row.target_system}
                </td>
                <td className="mono text-sm" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {row.new_value}
                </td>
                <td>
                  {row.conflict_detected ? (
                    <span className="badge badge-warning">{row.resolution_policy || 'CONFLICT'}</span>
                  ) : (
                    <span className="badge badge-success">SYNCED</span>
                  )}
                </td>
              </tr>
            ))}
            {audit.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                No events found.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Conflicts ────────────────────────────────────────────────────────────────

function ConflictsPage({ conflicts, onRefresh }) {
  return (
    <div>
      <div className="page-title">
        <h2>Conflict Resolution Log</h2>
        <p>Records of simultaneous edits and how SyncKar policies resolved them.</p>
      </div>
      <div className="table-container">
        <div className="table-header">
          <h3>Resolved Conflicts ({conflicts.length})</h3>
          <button className="btn btn-outline btn-sm" onClick={onRefresh}>Refresh Log</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Target ID</th>
              <th>Field</th>
              <th>Policy Applied</th>
              <th>Accepted Value</th>
              <th>Rejected Value</th>
            </tr>
          </thead>
          <tbody>
            {conflicts.map((c, i) => (
              <tr key={i}>
                <td className="mono">{c.created_at?.slice(0, 19).replace('T', ' ')}</td>
                <td><span className="badge badge-neutral">{c.ubid}</span></td>
                <td>{c.field}</td>
                <td><span className="badge badge-warning">{c.policy_applied}</span></td>
                <td className="mono text-sm" style={{ color: 'var(--status-success)' }}>{c.winning_value?.slice(0, 40)}</td>
                <td className="mono text-sm" style={{ color: 'var(--text-muted)', textDecoration: 'line-through' }}>{c.losing_value?.slice(0, 40)}</td>
              </tr>
            ))}
            {conflicts.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                No conflicts recorded.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── DLQ ─────────────────────────────────────────────────────────────────────

function DLQPage({ dlq }) {
  return (
    <div>
      <div className="page-title">
        <h2>Dead Letter Queue (DLQ)</h2>
        <p>Messages that failed to process after maximum retries.</p>
      </div>
      <div className="table-container">
        <div className="table-header">
          <h3>Failed Events ({dlq.length})</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Target ID</th>
              <th>Source</th>
              <th>Error Reason</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {dlq.map((item, i) => (
              <tr key={i}>
                <td className="mono">{item.created_at?.slice(0, 19).replace('T', ' ')}</td>
                <td><span className="badge badge-neutral">{item.ubid}</span></td>
                <td>{item.source_system}</td>
                <td className="mono text-sm" style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.error_reason}</td>
                <td><span className="badge badge-error">{item.status}</span></td>
                <td><button className="btn btn-outline btn-sm">Retry</button></td>
              </tr>
            ))}
            {dlq.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                DLQ is currently empty.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Verify ───────────────────────────────────────────────────────────────────

function VerifyPage({ audit, verifyResult, onVerify, onFetchAudit }) {
  useEffect(() => { onFetchAudit() }, [onFetchAudit])

  return (
    <div>
      <div className="page-title">
        <h2>BSA Verification</h2>
        <p>Cryptographically verify the integrity of SyncKar data propagations.</p>
      </div>
      <div className="table-container">
        <div className="table-header">
          <h3>Recent Audit Records</h3>
        </div>
        <table>
          <thead>
            <tr>
              <th>Trace ID</th>
              <th>Target ID</th>
              <th>Property Modified</th>
              <th>Vector</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {audit.slice(0, 10).map((row, i) => (
              <tr key={i}>
                <td className="mono text-sm">{row.audit_id?.slice(0, 12)}...</td>
                <td><span className="badge badge-neutral">{row.ubid}</span></td>
                <td>{row.field_modified}</td>
                <td className="text-sm">{row.source_system} &rarr; {row.target_system}</td>
                <td>
                  <button className="btn btn-primary btn-sm" onClick={() => onVerify(row.audit_id)}>
                    Verify Integrity
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {verifyResult && (
        <div className="verify-card">
          <div className={`verify-result ${verifyResult.signature_valid ? 'valid' : 'invalid'}`}>
            {verifyResult.signature_valid ? (
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
            ) : (
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
              </svg>
            )}
            <div>
              <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', fontWeight: 700 }}>
                {verifyResult.signature_valid ? 'Signature Valid' : 'Tamper Detected'}
              </h3>
              <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                BSA 2023 Compliance Status: <strong>{verifyResult.bsa_2023_compliant ? 'VERIFIED' : 'FAILED'}</strong>
              </p>
              
              <div className="verify-details">
                <div><strong>Audit ID:</strong> {verifyResult.audit_id}</div>
                <div><strong>SHA-256 Hash:</strong> {verifyResult.payload_sha256}</div>
                <div><strong>Target Entity:</strong> {verifyResult.verification_details?.ubid}</div>
                <div><strong>Property:</strong> {verifyResult.verification_details?.field}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
