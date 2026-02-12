import { useState } from "react";
import Layout from "../components/Layout";
import "../styles/app.css";
import { api } from "../lib/api";
import { auth, GoogleAuthProvider, signInWithPopup } from "../lib/firebase";

export default function SignupModern() {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole]   = useState("patient");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || "").trim());
  const isPhone = (s) => /^\+?\d{7,15}$/.test((s || "").trim());
  const readMsg = (e) => e?.response?.data?.detail || e?.message || "Something went wrong";

  async function handleSignup(e){
    e?.preventDefault?.();
    setMsg(""); setErr("");

    if (!isEmail(email)) { setErr("Enter a valid email."); return; }
    if (!isPhone(phone)) { setErr("Enter a valid phone (e.g. +2547XXXXXXXX)."); return; }

    try{
      setLoading(true);
      // Create user in your DB so clinicians can find them immediately (patient row auto if role=patient)
      await api.post("/auth/pre-register", {
        email: email.trim(),
        phone: phone.trim(),
        role,
        create_patient: role === "patient"
      }).catch(() => {}); // don’t block UX if this endpoint isn’t present yet

      setMsg("Account created. Redirecting to login…");
      setTimeout(()=> window.location.href = "/login-modern", 900);
    }catch(e){
      setErr(readMsg(e));
    }finally{
      setLoading(false);
    }
  }

  async function googleSignup(){
    setMsg(""); setErr("");
    try{
      setLoading(true);
      const provider = new GoogleAuthProvider();
      const cred = await signInWithPopup(auth, provider);
      const idToken = await cred.user.getIdToken();

      // Upsert in backend; also ensures patient row when role=patient
      await api.post("/auth/firebase/login", {
        id_token: idToken,
        chosen_role: role,
        ensure_patient: role === "patient"
      }).catch(()=>{});

      setMsg("Google account linked. Redirecting to login…");
      setTimeout(()=> window.location.href = "/login-modern", 900);
    }catch(e){
      setErr(readMsg(e));
    }finally{
      setLoading(false);
    }
  }

  return (
    <Layout title="Sign up">
      <div style={{display:"flex", justifyContent:"center", padding:"24px"}}>
        <form className="auth-card" onSubmit={handleSignup} style={{margin:"0 auto"}}>
          <div className="h2">Create an account</div>
          <div className="muted" style={{marginTop:6}}>
            Sign up with your <b>Email and Phone</b>, or use Google.
          </div>

          <input
            className="input"
            placeholder="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e)=>setEmail(e.target.value)}
          />

          <input
            className="input"
            placeholder="Phone (e.g. +2547XXXXXXXX)"
            type="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e)=>setPhone(e.target.value)}
          />

          <label className="muted" style={{marginTop:10}}>Choose role</label>
          <select className="input" value={role} onChange={(e)=>setRole(e.target.value)}>
            <option value="patient">Patient</option>
            <option value="clinician">Clinician</option>
            <option value="doctor">Doctor</option>
            <option value="admin">Admin</option>
          </select>

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Please wait…" : "Continue"}
          </button>

          <div style={{height:8}} />
          <button className="btn secondary" type="button" onClick={googleSignup} disabled={loading}>
            Continue with Google
          </button>

          {msg && <div style={{color:"#0E7ABF", marginTop:8}}>{msg}</div>}
          {err && <div style={{color:"crimson", marginTop:8}}>{err}</div>}

          <div style={{marginTop:12}}>
            Already have an account? <a href="/login-modern">Log in</a>
          </div>
        </form>
      </div>
    </Layout>
  );
}
