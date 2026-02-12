import { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout'
import '../styles/app.css'
import { api } from '../lib/api'

export default function DoctorPatients(){
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)

  // advice modal state
  const [adviceOpen, setAdviceOpen] = useState(false)
  const [adviceText, setAdviceText] = useState('')

  // -------------- helpers --------------
  async function resolvePatient(term){
    const q = (term || '').trim()
    if (!q) return null

    // 1) numeric → treat as patient_id
    if (/^\d+$/.test(q)) return Number(q)

    // 2) email → exact match using resolver
    if (q.includes('@')) {
      try {
        const { data } = await api.get(`/patients/resolve`, { params: { q, create_if_missing: false } })
        if (data?.id) return data.id
      } catch(_) {}
    }

    // 3) fallback: search list and pick exact match
    try {
      const { data } = await api.get('/patients', { params: { q } })
      const rows = Array.isArray(data) ? data : []
      const lower = q.toLowerCase()
      const exact = rows.find(r =>
        (r.email || '').toLowerCase() === lower ||
        (r.full_name || '').toLowerCase() === lower
      )
      if (exact?.id) return exact.id
      if (rows.length === 1 && rows[0]?.id) return rows[0].id
    } catch(_){}

    return null
  }

  // -------------- data loaders --------------
  async function fetchPatients(term){
    try{
      setLoading(true); setError('')
      const { data } = await api.get('/patients', { params: term ? { q: term } : {} })
      const cleaned = (data || []).filter(p => p && typeof p.id === 'number')
      setPatients(cleaned)
      if (cleaned.length && !selectedId) setSelectedId(cleaned[0].id)
    }catch(e){
      setError('Failed to load patients')
    }finally{
      setLoading(false)
    }
  }

  async function loadDetail(idOrTerm){
    if (idOrTerm == null) return
    let id = idOrTerm
    if (typeof idOrTerm !== 'number') {
      id = await resolvePatient(idOrTerm)
    }
    if (typeof id !== 'number') { setSelected(null); return }
    try{
      // base patient detail
      const { data } = await api.get(`/patients/${id}`)

      // IMPORTANT: use the SAME endpoint the Patient page uses:
      // GET /gh/latest/:patient_id
      let prediction = null
      try {
        const pr = await api.get(`/gh/latest/${id}`)
        prediction = pr?.data ?? null
      } catch(_) {}

      setSelected({ ...(data || {}), prediction })
      setSelectedId(id)
    }catch(_){
      setSelected(null)
    }
  }

  useEffect(()=>{ fetchPatients('') },[])
  useEffect(()=>{ if (selectedId!=null) loadDetail(selectedId) },[selectedId])

  const filtered = useMemo(()=>{
    if (!search) return patients
    const s = search.toLowerCase()
    return patients.filter(p =>
      (p.full_name || '').toLowerCase().includes(s) ||
      (p.email || '').toLowerCase().includes(s)
    )
  }, [patients, search])

  async function saveAdvice(e){
    if (e?.preventDefault) e.preventDefault()
    try{
      if (!selected?.id || typeof selected.id !== 'number') {
        alert('Select a valid patient first')
        return
      }
      const body = { advice: adviceText.trim() }
      if (!body.advice) { alert('Advice cannot be empty'); return }

      await api.post(`/patients/${selected.id}/advice`, body)
      setAdviceOpen(false)
      setAdviceText('')
      await loadDetail(selected.id) // refresh to show newly added advice
    }catch(err){
      const msg =
        err?.response?.data?.detail ||
        (Array.isArray(err?.response?.data)
          ? err.response.data.map(x => x.msg).join(', ')
          : '') ||
        'Failed to save advice'
      alert(msg)
      console.error('saveAdvice error:', err?.response?.data || err)
    }
  }

  return (
    <Layout title="Doctor Dashboard">
      <div className="grid" style={{gridTemplateColumns:'340px 1fr', gap:18}}>
        {/* Left list */}
        <div className="card" style={{padding:0, overflow:'hidden'}}>
          <div style={{padding:16, borderBottom:'1px solid #eee'}}>
            <input
              className="input"
              placeholder="Search patients by name, email, or ID"
              value={search}
              onChange={e=>{
                const v = e.target.value
                setSearch(v)
                fetchPatients(v)
              }}
              onKeyDown={async (e)=>{
                if (e.key === 'Enter' && search.trim()){
                  const resolved = await resolvePatient(search)
                  if (resolved) setSelectedId(resolved)
                }
              }}
            />
          </div>
          {loading ? (
            <div style={{padding:16}}>Loading…</div>
          ) : error ? (
            <div style={{padding:16, color:'crimson'}}>{error}</div>
          ) : (
            <div style={{maxHeight: '60vh', overflowY:'auto'}}>
              {filtered.length === 0 ? (
                <div style={{padding:16, color:'#666'}}>No patients found.</div>
              ) : filtered.map(p => (
                <div
                  key={p.id}
                  onClick={()=>setSelectedId(p.id)}
                  style={{
                    padding:'12px 16px',
                    borderBottom:'1px solid #f1f1f1',
                    cursor:'pointer',
                    background: p.id===selectedId ? '#F0FAFF' : 'transparent'
                  }}
                >
                  <div style={{fontWeight:600}}>{p.full_name || '(no name)'}</div>
                  <div className="muted">{p.email}</div>
                  {p.phone_number && <div className="muted">{p.phone_number}</div>}
                  {/* ANC status removed from doctor per requirement */}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right detail */}
        <div className="grid" style={{gap:18}}>
          {!selected ? (
            <div className="card">Select a patient to view details.</div>
          ) : (
            <>
              <div className="card">
                <div className="h2">
                  {selected.full_name || '(no name)'}{' '}
                  <span className="muted" style={{fontSize:14}}>· {selected.email}</span>
                </div>
                <div className="muted" style={{marginTop:6}}>Phone: {selected.phone_number || '—'}</div>
                <div style={{height:12}}/>
                <button className="btn" onClick={()=>setAdviceOpen(true)}>Add Advice</button>
              </div>

              {/* Latest Prediction visible to doctor */}
              <div className="card">
                <div className="h3">Latest Prediction</div>
                {selected.prediction ? (
                  <div style={{marginTop:8}}>
                    <div className="grid" style={{gridTemplateColumns:'1fr 1fr 1fr', gap:12}}>
                      <div className="tile"><div className="label">Risk Class</div><div className="value">{selected.prediction.risk_class ?? '—'}</div></div>
                      <div className="tile"><div className="label">Score</div><div className="value">{selected.prediction.risk_score ?? '—'}</div></div>
                      <div className="tile"><div className="label">Priority</div><div className="value">{selected.prediction.priority ? 'Yes' : 'No'}</div></div>
                    </div>
                    {Array.isArray(selected.prediction.reasons) && selected.prediction.reasons.length > 0 && (
                      <div className="muted" style={{marginTop:8}}>
                        Reasons: {selected.prediction.reasons.join(', ')}
                      </div>
                    )}
                    {selected.prediction.created_at && (
                      <div className="muted" style={{marginTop:8, fontSize:12}}>
                        Assessed on: {new Date(selected.prediction.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="muted" style={{marginTop:8}}>No prediction found for this patient.</div>
                )}
              </div>

              <div className="card">
                <div className="h3">Advice</div>
                {selected.advice?.length ? (
                  <ul style={{marginTop:8}}>
                    {selected.advice.map(a=>(
                      <li key={a.id || `${a.created_at}-${a.text?.slice(0,12)}`} className="muted" style={{marginBottom:6}}>
                        {a.text}{' '}
                        <span style={{fontSize:12, opacity:.7}}>
                          · {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="muted" style={{marginTop:6}}>No advice yet.</div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Advice modal */}
      {adviceOpen && (
        <div className="modal">
          <form className="modal-card" onSubmit={saveAdvice}>
            <div className="h3">Advice for {selected?.full_name || selected?.email || 'patient'}</div>
            <textarea
              className="input"
              rows={6}
              value={adviceText}
              onChange={e=>setAdviceText(e.target.value)}
              placeholder="Type your clinical advice…"
              required
            />
            <div style={{display:'flex', gap:10, marginTop:12}}>
              <button type="submit" className="btn">Save Advice</button>
              <button type="button" className="btn secondary" onClick={()=>setAdviceOpen(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}
    </Layout>
  )
}
