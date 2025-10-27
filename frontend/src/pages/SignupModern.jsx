import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import '../styles/app.css'
import { api } from '../lib/api'
import { extractErrMessage } from '../lib/errors'
import { setAuth } from '../lib/auth'

export default function SignupModern(){
  const nav = useNavigate()
  const [uid,setUid]=useState('')          // display name
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [confirm,setConfirm]=useState('')
  const [role,setRole]=useState('patient')
  const [msg,setMsg]=useState('')

  async function go(){
    if(password!==confirm){ setMsg('Passwords do not match'); return }
    try{
      setMsg('')
      const {data} = await api.post('/auth/signup',{email,password,full_name:uid,role})
      const displayName = uid?.trim() || (email.includes('@') ? email.split('@')[0] : email)
      setAuth({ email, role: data.role, displayName })
      if(data.role==='patient') nav('/patient/dashboard/me', { replace:true })
      else if(data.role==='clinician') nav('/clinician/dashboard', { replace:true })
      else if(data.role==='doctor') nav('/doctor/patients', { replace:true })
      else nav('/admin/users', { replace:true })
    }catch(e){ setMsg(extractErrMessage(e)) }
  }

  return (
    <div className="auth-shell">
      <div className="auth-left"><div className="logo"><div className="logo" style={{width:42,height:42,borderRadius:12}}></div><span>HealthGuard</span></div></div>
      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-title">Create your account</div>
          <div className="auth-sub">Join our community of healthcare professionals and patients.</div>
          <input className="input" placeholder="User ID (display name)" value={uid} onChange={e=>setUid(e.target.value)} />
          <input className="input" placeholder="Email address" value={email} onChange={e=>setEmail(e.target.value)} />
          <input className="input" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          <input className="input" type="password" placeholder="Confirm Password" value={confirm} onChange={e=>setConfirm(e.target.value)} />
          <select className="select" value={role} onChange={e=>setRole(e.target.value)}>
            <option value="patient">Patient</option><option value="clinician">Clinician</option><option value="doctor">Doctor</option><option value="admin">Administrator</option>
          </select>
          <button className="btn" onClick={go}>Sign Up</button>
          {msg && <div className="muted" style={{color:'crimson'}}>{msg}</div>}
          <div style={{textAlign:'center'}}>Already have an account? <Link className="link" to="/login-modern">Log in</Link></div>
        </div>
      </div>
    </div>
  )
}
