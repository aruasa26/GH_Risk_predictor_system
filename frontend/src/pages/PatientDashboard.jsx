// frontend/src/pages/PatientDashboard.jsx
import { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import '../styles/app.css'
import { api } from '../lib/api'
import { getDisplayName } from '../lib/auth'

function getEmail(){
  try{
    const raw = localStorage.getItem('auth')
    if (!raw) return null
    const obj = JSON.parse(raw)
    return obj?.email || null
  }catch{ return null }
}

// --- unified resolver (matches clinician flow) ---
async function resolvePatientId(term){
  if (!term) return null
  const q = term.trim()
  // 1) primary: server resolver (handles email OR id; same path clinician uses)
  try{
    const r = await api.get('/patients/resolve', { params: { q } })
    if (r?.data?.id) return r.data.id
  }catch(_){}

  // 2) exact email fallback
  if (q.includes('@')){
    try{
      const r = await api.get(`/patients/by-email/${encodeURIComponent(q)}`)
      if (r?.data?.id) return r.data.id
    }catch(_){}
  }

  // 3) last resort: search list and pick exact match by email
  try{
    const r = await api.get('/patients', { params: { q } })
    const rows = Array.isArray(r?.data) ? r.data : []
    const s = q.toLowerCase()
    const exact = rows.find(p => (p?.email || '').toLowerCase() === s)
    return exact?.id ?? null
  }catch(_){}

  return null
}

export default function PatientDashboard(){
  const [nextVisit, setNextVisit] = useState(null)
  const [advice, setAdvice] = useState([])
  const [loadingAdvice, setLoadingAdvice] = useState(true)

  // latest GH risk
  const [risk, setRisk] = useState(null)
  const [riskLoading, setRiskLoading] = useState(true)
  const [riskError, setRiskError] = useState('')

  const name = getDisplayName() || 'Patient'
  const email = getEmail()

  async function loadNextVisit(){
    try{
      if (!email) return
      const {data} = await api.get('/visits/gh/me/next-visit', { params: { email } })
      setNextVisit(data?.next_visit || null)
    }catch{ setNextVisit(null) }
  }

  async function loadAdvice(){
    try{
      if (!email) return
      setLoadingAdvice(true)
      const { data } = await api.get(`/patients/by-email/${encodeURIComponent(email)}`)
      setAdvice(data?.advice || [])
    }catch{ setAdvice([]) }
    finally{ setLoadingAdvice(false) }
  }

  // load the latest saved GH prediction for THIS patient
  async function loadRisk(){
    setRiskLoading(true)
    setRiskError('')
    try{
      if (!email) { setRisk(null); return }
      const pid = await resolvePatientId(email)
      if (!pid){ setRisk(null); return }
      const { data } = await api.get(`/gh/latest/${pid}`)
      setRisk(data || null)
    }catch(e){
      // if backend says 404, treat as "no prediction yet" instead of error banner
      const status = e?.response?.status
      if (status === 404){
        setRisk(null)
        setRiskError('')
      }else{
        setRisk(null)
        const msg = e?.response?.data?.detail || e?.message || 'Failed to load your latest risk'
        setRiskError(msg)
      }
    }finally{
      setRiskLoading(false)
    }
  }

  async function reschedule(){
    try{
      if (!email) return alert('No email found for your account')
      const { data: me } = await api.get(`/patients/by-email/${encodeURIComponent(email)}`)
      const pid = me?.id
      if (!pid) return alert('Could not resolve your patient profile')

      const val = prompt('Pick a new date (YYYY-MM-DD) within 7 days of current plan:', nextVisit || '')
      if (!val) return
      await api.post('/visits/reschedule', { patient_id: pid, new_date: val })
      await loadNextVisit()
      alert('Rescheduled successfully')
    }catch(e){
      const msg = e?.response?.data?.detail
        || (Array.isArray(e?.response?.data) ? e.response.data.map(x=>x.msg).join(', ') : '')
        || 'Reschedule failed'
      alert(msg)
    }
  }

  useEffect(()=>{ loadNextVisit(); loadAdvice(); loadRisk() },[]) // run once

  const badge = r => r==='High'
    ? 'badge high'
    : r==='Moderate'
      ? 'badge moderate'
      : 'badge low'

  return (
    <Layout title="Patient Dashboard">
      <div className="grid" style={{gridTemplateColumns:'1fr 360px', gap:18}}>
        <div className="grid" style={{gap:18}}>
          <div className="card">
            <div className="h2">Welcome back, {name}. Here's your health overview.</div>
          </div>

          {/* Latest GH risk panel */}
          <div className="card">
            <div className="h3">Your Latest GH Risk</div>
            {riskLoading ? (
              <div className="muted" style={{marginTop:8}}>Loading your latest prediction…</div>
            ) : riskError ? (
              <div className="muted" style={{marginTop:8, color:'crimson'}}>{riskError}</div>
            ) : !risk ? (
              <div className="muted" style={{marginTop:8}}>
                No recorded prediction yet. Please ask your clinician to run a GH risk assessment.
              </div>
            ) : (
              <>
                <div className="kpi" style={{marginTop:6}}>
                  <div className="muted">Predicted Risk</div>
                  <div className="big">{risk.risk_class}</div>
                  <div className={badge(risk.risk_class)} style={{marginTop:8}}>
                    score {risk.risk_score}
                  </div>
                </div>
                {(risk.priority || (risk.reasons && risk.reasons.length>0)) && (
                  <div style={{marginTop:12}}>
                    {risk.priority && <span className="badge high">🚑 Priority High</span>}
                    {Array.isArray(risk.reasons) && risk.reasons.length>0 && (
                      <>
                        <div className="muted" style={{marginTop:10, marginBottom:6}}>Why flagged</div>
                        <div style={{display:'flex', flexWrap:'wrap', gap:6}}>
                          {risk.reasons.map((r,i)=>(
                            <span key={i} className="badge" style={{background:'#eef2f7', color:'#0b213f'}}>{r}</span>
                          ))}
                        </div>
                      </>
                    )}
                    {risk.created_at && (
                      <div className="muted" style={{marginTop:10, fontSize:12}}>
                        Assessed on: {new Date(risk.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="card">
            <div className="h3">Doctor’s Advice</div>
            {loadingAdvice ? (
              <div className="muted" style={{marginTop:8}}>Loading advice…</div>
            ) : advice.length === 0 ? (
              <div className="muted" style={{marginTop:8}}>No advice yet.</div>
            ) : (
              <ul style={{marginTop:8}}>
                {advice.map(a=>(
                  <li key={a.id} className="muted" style={{marginBottom:6}}>
                    {a.text}{' '}
                    <span style={{fontSize:12, opacity:.7}}>
                      · {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="banner">
            <div>
              <div style={{fontWeight:800}}>📣 Upcoming Visit Reminder</div>
              <div className="muted">Your next ANC visit may be approaching. Confirm or reschedule if necessary.</div>
            </div>
            <button className="btn secondary" onClick={()=>alert('Attendance confirmed.')}>Confirm Attendance</button>
          </div>
        </div>

        <div className="grid right-col">
          <div className="card">
            <div className="h3">Next ANC Visit</div>
            <div style={{fontSize:28, fontWeight:800, color:'#0E7ABF'}}>{nextVisit || '—'}</div>
            <div className="muted" style={{marginTop:8}}>Ensure you attend this appointment for a comprehensive check-up.</div>
            <div style={{height:8}}/>
            <button className="btn secondary" onClick={reschedule}>Reschedule</button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
