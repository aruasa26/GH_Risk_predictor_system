import { useMemo, useState } from 'react'
import Layout from '../components/Layout'
import '../styles/app.css'
import { api } from '../lib/api'

export default function ClinicianDashboard(){
  const [form, setForm] = useState({
    patient_id:'',
    age:'',           // number
    bmi:'',           // number
    systolic_bp:'',   // number
    diastolic_bp:'',  // number
    previous_complications:false, // 0/1
    preexisting_diabetes:false,   // 0/1
    gestational_diabetes:false,   // 0/1
    mental_health:false,          // 0/1
    heart_rate:'',    // number
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [triage, setTriage] = useState({reasons: [], tier: null})

  const set = (k,v)=> setForm(s=>({...s,[k]:v}))
  const toInt = v => v==='' ? undefined : parseInt(v,10)
  const toFloat = v => v==='' ? undefined : parseFloat(v)

  function localTriageExplain(payload){
    const reasons = []
    if (Number.isFinite(payload.systolic_bp) && payload.systolic_bp >= 140) reasons.push(`SBP ≥ 140 (${payload.systolic_bp})`)
    if (Number.isFinite(payload.diastolic_bp) && payload.diastolic_bp >= 90) reasons.push(`DBP ≥ 90 (${payload.diastolic_bp})`)
    if (
      Number.isFinite(payload.systolic_bp) && Number.isFinite(payload.diastolic_bp) &&
      payload.systolic_bp >= 130 && payload.diastolic_bp >= 85
    ) reasons.push(`SBP ≥ 130 & DBP ≥ 85 (${payload.systolic_bp}/${payload.diastolic_bp})`)
    if (Number.isFinite(payload.bmi) && payload.bmi >= 35) reasons.push(`BMI ≥ 35 (${payload.bmi})`)
    if (Number.isFinite(payload.age) && (payload.age < 18 || payload.age > 40)) reasons.push(`Age high-risk (${payload.age})`)
    if (payload.previous_complications === 1) reasons.push('Previous complications')
    if (payload.preexisting_diabetes === 1) reasons.push('Pre-existing diabetes')
    if (payload.gestational_diabetes === 1) reasons.push('Gestational diabetes')
    if (payload.mental_health === 1) reasons.push('Diagnosed mental health condition')
    return reasons
  }

  // ========= resolver: supports numeric ID or email =========
  async function resolvePatientId(q){
    if (!q) return null
    const term = q.trim()

    try {
      // robust resolver (server-side): can accept ID or email; can auto-create if email
      const r = await api.get('/patients/resolve', { params: { q: term, create_if_missing: true } })
      if (r?.data?.id) return r.data.id
    } catch (_) {}

    // fallbacks
    if (/^\d+$/.test(term)) {
      try { const r = await api.get(`/patients/${term}`); if (r?.data?.id) return r.data.id } catch(_){}
    }
    if (term.includes('@')) {
      try { const r = await api.get(`/patients/by-email/${encodeURIComponent(term)}`); if (r?.data?.id) return r.data.id } catch(_){}
    }
    return null
  }

  async function predict(){
    try{
      setLoading(true)
      setResult(null)
      setTriage({reasons: [], tier: null})

      const pidInput = (form.patient_id || '').trim()
      let resolvedId = null
      if (pidInput) {
        resolvedId = await resolvePatientId(pidInput)
        if (!resolvedId) {
          alert('Could not resolve patient by that ID or email. Prediction will run but won’t be linked.')
        }
      }

      const payload = {
        // 🔧 FIX: backend expects string; resolver may return number
        patient_id: resolvedId != null ? String(resolvedId) : undefined,

        age: Number(form.age),
        bmi: Number(form.bmi),
        systolic_bp: Number(form.systolic_bp),
        diastolic_bp: Number(form.diastolic_bp),
        previous_complications: form.previous_complications ? 1 : 0,
        preexisting_diabetes:  form.preexisting_diabetes  ? 1 : 0,
        gestational_diabetes:  form.gestational_diabetes  ? 1 : 0,
        mental_health:         form.mental_health         ? 1 : 0,
        heart_rate: Number(form.heart_rate),
      }

      const mustBeInt   = ['age','systolic_bp','diastolic_bp','heart_rate']
      const mustBeNum   = ['bmi']
      for (const k of [...mustBeInt, ...mustBeNum]){
        if (!Number.isFinite(payload[k])) {
          alert(`Please enter a valid value for "${k.replace('_',' ')}"`)
          setLoading(false); return
        }
      }
      if (payload.age < 10 || payload.age > 60) { alert('Age must be 10–60'); setLoading(false); return }
      if (payload.bmi < 10 || payload.bmi > 60) { alert('BMI must be 10–60'); setLoading(false); return }
      if (payload.systolic_bp < 60 || payload.systolic_bp > 250) { alert('Systolic BP must be 60–250'); setLoading(false); return }
      if (payload.diastolic_bp < 40 || payload.diastolic_bp > 150) { alert('Diastolic BP must be 40–150'); setLoading(false); return }
      if (payload.heart_rate < 40 || payload.heart_rate > 220) { alert('Heart rate must be 40–220'); setLoading(false); return }

      const {data} = await api.post('/gh/predict-gh', payload)
      setResult(data)

      const reasons = Array.isArray(data?.reasons) && data.reasons.length
        ? data.reasons
        : localTriageExplain(payload)

      const tier =
        data?.priority ? 'Priority High'
        : (data?.risk_class === 'High' ? 'Screened High' : 'Low')

      setTriage({reasons, tier})
    }catch(e){
      const detail =
        e?.response?.data?.detail ??
        e?.response?.data ??
        e?.message ??
        'Prediction failed'
      const msg = typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2)
      alert(msg)
      console.error('predict error:', e?.response?.data || e)
    }finally{
      setLoading(false)
    }
  }

  const badge = r => r==='High' ? 'badge high' : r==='Moderate' ? 'badge moderate' : 'badge low'

  // ========== ANC scheduling (unchanged) ==========
  const [anc, setAnc] = useState({
    q: '',            // email OR ID
    last_visit: '',   // YYYY-MM-DD
    requested_next: ''// YYYY-MM-DD (within window)
  })
  const [saving, setSaving] = useState(false)
  const setAncField = (k,v)=> setAnc(s=>({...s,[k]:v}))

  const windowText = useMemo(()=>{
    if (!anc.last_visit) return ''
    try{
      const base = new Date(anc.last_visit)
      const min = new Date(base); min.setDate(min.getDate()+21)
      const max = new Date(base); max.setDate(max.getDate()+35)
      const f = d => d.toISOString().slice(0,10)
      return `${f(min)} → ${f(max)} (allowed window)`
    }catch{ return '' }
  }, [anc.last_visit])

  async function scheduleANC(e){
    e?.preventDefault?.()
    try{
      setSaving(true)
      if (!anc.q.trim()) { alert('Enter patient email'); setSaving(false); return }
      if (!anc.last_visit) { alert('Select the last visit date'); setSaving(false); return }

      const patientId = await resolvePatientId(anc.q.trim())
      if (!patientId) { alert('Patient not found'); setSaving(false); return }

      const payload = {
        patient_id: patientId,
        last_visit: anc.last_visit,
        requested_next: anc.requested_next || null
      }

      await api.post('/visits/schedule', payload)
      alert('ANC visit scheduled successfully')
      setAnc(s=>({ ...s, requested_next:'' }))

    }catch(e){
      const msg = e?.response?.data?.detail
        || (typeof e?.response?.data === 'string' ? e.response.data : '')
        || e?.message || 'Failed to schedule ANC visit'
      alert(msg)
    }finally{ setSaving(false) }
  }

  // ================================================================
  // ========= Clinician patient lookup for status + prediction + advice
  // ================================================================
  const [lookup, setLookup] = useState('')
  const [overview, setOverview] = useState(null)
  const [overviewLoading, setOverviewLoading] = useState(false)

  async function loadOverview(){
    if (!lookup.trim()) return
    setOverviewLoading(true)
    setOverview(null)
    try{
      const pid = await resolvePatientId(lookup.trim())
      if (!pid) { alert('Patient not found'); setOverviewLoading(false); return }

      // 1) base profile (NOTE: correct path is /patients/:id — not /patients/by-id/:id)
      const prof = await api.get(`/patients/${pid}`)
      const profile = prof?.data || {}
      const email = profile?.email || null
      const advice = Array.isArray(profile?.advice) ? profile.advice : []

      // 2) latest prediction (same endpoint used by PatientDashboard)
      let prediction = null
      try{
        const pr = await api.get(`/gh/latest/${pid}`)
        prediction = pr?.data ?? null
      }catch(_){}

      // 3) ANC schedule (same endpoint as patient flow, needs email)
      let visit = null
      if (email){
        try{
          const vr = await api.get('/visits/gh/me/next-visit', { params: { email } })
          visit = vr?.data ?? null // { next_visit: 'YYYY-MM-DD', status? }
        }catch(_){}
      }

      setOverview({
        email,
        prediction,
        visit,     // { next_visit, status? }
        advice     // array
      })
    }catch(e){
      console.error(e)
      alert('Failed to load patient overview')
    }finally{
      setOverviewLoading(false)
    }
  }

  return (
    <Layout title="Clinician Dashboard">
      <div className="grid grid-2">
        <div className="card">
          <div className="h3">Patient Characteristic Input</div>
          <div className="form">
            {/* === existing inputs remain unchanged === */}

            <input
              className="input"
              placeholder="Patient email"
              value={form.patient_id}
              onChange={e=>set('patient_id', e.target.value)}
            />

            <div className="grid" style={{gridTemplateColumns:'1fr 1fr', gap:10}}>
              <input className="input" type="number" min={10} max={60} step="1"
                     placeholder="Age (years)" value={form.age}
                     onChange={e=>set('age', e.target.value)} />
              <input className="input" type="number" min={10} max={60} step="0.1"
                     placeholder="BMI" value={form.bmi}
                     onChange={e=>set('bmi', e.target.value)} />
              <input className="input" type="number" min={60} max={250} step="1"
                     placeholder="Systolic BP (mmHg)" value={form.systolic_bp}
                     onChange={e=>set('systolic_bp', e.target.value)} />
              <input className="input" type="number" min={40} max={150} step="1"
                     placeholder="Diastolic BP (mmHg)" value={form.diastolic_bp}
                     onChange={e=>set('diastolic_bp', e.target.value)} />
              <input className="input" type="number" min={40} max={200} step="1"
                     placeholder="Heart Rate (bpm)" value={form.heart_rate}
                     onChange={e=>set('heart_rate', e.target.value)} />
            </div>

            <label className="full" style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10, marginTop:8}}>
              <label style={{display:'flex',gap:8,alignItems:'center'}}>
                <input type="checkbox" checked={form.previous_complications}
                       onChange={e=>set('previous_complications', e.target.checked)} />
                Previous Complications
              </label>
              <label style={{display:'flex',gap:8,alignItems:'center'}}>
                <input type="checkbox" checked={form.preexisting_diabetes}
                       onChange={e=>set('preexisting_diabetes', e.target.checked)} />
                Preexisting Diabetes
              </label>
              <label style={{display:'flex',gap:8,alignItems:'center'}}>
                <input type="checkbox" checked={form.gestational_diabetes}
                       onChange={e=>set('gestational_diabetes', e.target.checked)} />
                Gestational Diabetes
              </label>
              <label style={{display:'flex',gap:8,alignItems:'center'}}>
                <input type="checkbox" checked={form.mental_health}
                       onChange={e=>set('mental_health', e.target.checked)} />
                Mental Health (diagnosed)
              </label>
            </label>

            {/* ===== ANC section (unchanged) ===== */}
            <div className="full" style={{marginTop:16, paddingTop:12, borderTop:'1px solid #eef2f7'}}>
              <div className="h3" style={{marginBottom:8}}>ANC Visit — Schedule / Update</div>
              <div className="muted" style={{marginBottom:8}}>
                Enter the patient’s <b>email or ID</b> and the last visit date. Optionally choose a next visit date within the allowed window.
              </div>

              <div className="grid" style={{gap:10}}>
                <input
                  className="input"
                  placeholder="Patient email or ID (e.g. test8@gmail.com or 123)"
                  value={anc.q}
                  onChange={e=>setAncField('q', e.target.value)}
                />

                <label className="full muted" style={{marginTop:4}}>Last Visit Date</label>
                <input
                  className="input"
                  type="date"
                  value={anc.last_visit}
                  onChange={e=>setAncField('last_visit', e.target.value)}
                />

                <label className="full muted" style={{marginTop:6}}>
                  Optional Requested Next Visit (must be within 3–5 weeks of last visit)
                  {anc.last_visit && <div style={{marginTop:4, fontWeight:600, color:'#0E7ABF'}}>{windowText}</div>}
                </label>
                <input
                  className="input"
                  type="date"
                  value={anc.requested_next}
                  onChange={e=>setAncField('requested_next', e.target.value)}
                />

                <button className="btn" onClick={scheduleANC} disabled={saving}>
                  {saving ? 'Saving…' : '🗓️  Schedule Next ANC'}
                </button>
              </div>
            </div>
            {/* ======================================================== */}

          </div>
        </div>

        <div className="right-col">
          <div className="card">
            <div style={{height:8}}/>
            <button className="btn" onClick={predict} disabled={loading}>
              {loading?'Predicting…':'⚡ Predict GH Risk'}
            </button>
          </div>

          <div className="card">
            <div className="h3">Prediction Result</div>
            <div className="kpi">
              <div className="muted">Predicted Risk</div>
              <div className="big">{result ? result.risk_class : '—'}</div>
              {result && <div className={badge(result.risk_class)} style={{marginTop:8}}>score {result.risk_score}</div>}

              {result && (result.priority || triage.tier) && (
                <div style={{marginTop:10, display:'flex', gap:8, flexWrap:'wrap'}}>
                  {result.priority && (
                    <span className="badge high" title="High-precision band">🚑 Priority High</span>
                  )}
                  {!result.priority && result.risk_class==='High' && (
                    <span className="badge moderate" title="Screening band">Screened High</span>
                  )}
                  {!result.priority && triage.tier==='Priority High' && (
                    <span className="badge high">🚑 Priority High</span>
                  )}
                </div>
              )}
            </div>

            {result && (Array.isArray(result.reasons) ? result.reasons.length>0 : triage.reasons.length>0) && (
              <div style={{marginTop:14}}>
                <div className="muted" style={{marginBottom:6}}>Why flagged</div>
                <div style={{display:'flex', flexWrap:'wrap', gap:6}}>
                  {(Array.isArray(result.reasons) && result.reasons.length>0 ? result.reasons : triage.reasons).map((r,i)=>(
                    <span key={i} className="badge" style={{background:'#eef2f7', color:'#0b213f'}}>{r}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="muted" style={{marginTop:12}}>
              This prediction supports—not replaces—clinical judgment.
            </div>
          </div>

          {/* ===== Clinician Patient Lookup (status + prediction + advice) ===== */}
          <div className="card" style={{marginTop:16}}>
            <div className="h3">🔍 Patient Lookup</div>
            <div style={{display:'flex', gap:8, marginTop:8}}>
              <input
                className="input"
                placeholder="Email or numeric ID"
                value={lookup}
                onChange={e=>setLookup(e.target.value)}
              />
              <button className="btn" onClick={loadOverview} disabled={overviewLoading}>
                {overviewLoading ? 'Loading…' : 'Search'}
              </button>
            </div>

            {!overview ? (
              <div className="muted" style={{marginTop:10}}>Search a patient to view ANC status, latest prediction, and doctor’s advice.</div>
            ) : (
              <div style={{marginTop:12}}>
                <div className="h4">ANC Visit</div>
                <div className="muted">
                  {overview.visit && (overview.visit.next_visit || overview.visit.status)
                    ? <>
                        {overview.visit.status ? <span>Status: {overview.visit.status}</span> : null}
                        {(overview.visit.status && overview.visit.next_visit) ? ' · ' : null}
                        {overview.visit.next_visit ? <span>Next: {overview.visit.next_visit}</span> : null}
                      </>
                    : 'No visit record found.'}
                </div>

                <div className="h4" style={{marginTop:12}}>Latest Prediction</div>
                {overview.prediction ? (
                  <div>
                    <div><b>Risk:</b> {overview.prediction.risk_class} ({overview.prediction.risk_score})</div>
                    {Array.isArray(overview.prediction.reasons) && overview.prediction.reasons.length>0 && (
                      <div className="muted" style={{marginTop:4}}>
                        Reasons: {overview.prediction.reasons.join(', ')}
                      </div>
                    )}
                    {overview.prediction.created_at && (
                      <div className="muted" style={{marginTop:6, fontSize:12}}>
                        Assessed on: {new Date(overview.prediction.created_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="muted">No prediction found.</div>
                )}

                <div className="h4" style={{marginTop:12}}>Doctor’s Advice</div>
                {Array.isArray(overview.advice) && overview.advice.length > 0 ? (
                  <ul style={{marginTop:6}}>
                    {overview.advice.map(a=>(
                      <li key={a.id || `${a.created_at}-${a.text?.slice(0,12)}`} className="muted" style={{marginBottom:6}}>
                        {a.text}{' '}
                        <span style={{fontSize:12, opacity:.7}}>
                          · {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="muted">No advice yet.</div>
                )}
              </div>
            )}
          </div>
          {/* =============================================================== */}
        </div>
      </div>
    </Layout>
  )
}
