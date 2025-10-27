import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import '../styles/app.css'
import { api } from '../lib/api'
import { extractErrMessage } from '../lib/errors'
import { setAuth } from '../lib/auth'

export default function LoginModern(){
  const nav = useNavigate()
  const loc = useLocation()
  const [identifier,setIdentifier]=useState('') // email OR user id
  const [password,setPassword]=useState('')
  const [role,setRole]=useState('patient')
  const [msg,setMsg]=useState('')

  async function go(){
    try{
      setMsg('')
      const {data}=await api.post('/auth/login',{identifier,password,role})
      // data.user = { email, full_name, role }
      const displayName = data?.user?.full_name || (data?.user?.email?.split('@')[0] ?? 'User')
      setAuth({ email: data.user.email, role: data.user.role, displayName })
      const from = loc.state?.from
      if (from) return nav(from, { replace:true })
      if(data.user.role==='patient') nav('/patient/dashboard/me', { replace:true })
      else if(data.user.role==='clinician') nav('/clinician/dashboard', { replace:true })
      else if(data.user.role==='doctor') nav('/doctor/patients', { replace:true })
      else nav('/admin/users', { replace:true })
    }catch(e){ setMsg(extractErrMessage(e)) }
  }

  return (
    <div className="auth-shell">
      <div className="auth-left"><div className="logo"><div className="logo" style={{width:42,height:42,borderRadius:12}}></div><span>HealthGuard</span></div></div>
      <div className="auth-right">
        <div className="auth-card">
          <div className="auth-title">Welcome back</div>
          <div className="auth-sub">Login with your Email <b>or</b> User ID</div>
          <input className="input" placeholder="Email or User ID" value={identifier} onChange={e=>setIdentifier(e.target.value)} />
          <input className="input" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
          <select className="select" value={role} onChange={e=>setRole(e.target.value)}>
            <option value="patient">Patient</option><option value="clinician">Clinician</option><option value="doctor">Doctor</option><option value="admin">Admin</option>
          </select>
          <button className="btn" onClick={go}>Login</button>
          {msg && <div className="muted" style={{color:'crimson'}}>{msg}</div>}
          <div style={{textAlign:'center'}}><Link className="link" to="/signup-modern">Don’t have an account? Sign up</Link></div>
        </div>
      </div>
    </div>
  )
}
