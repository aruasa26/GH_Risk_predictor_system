// frontend/src/pages/LoginModern.jsx
import { useEffect, useRef, useState } from "react";
import Layout from "../components/Layout";
import "../styles/app.css";
import { api } from "../lib/api";
import {
  auth,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  sendSignInLinkToEmail,
  isSignInWithEmailLink,
  signInWithEmailLink,
  GoogleAuthProvider,
  signInWithPopup
} from "../lib/firebase";

const actionCodeSettings = {
  url: `${window.location.origin}/login-modern`,
  handleCodeInApp: true
};

const isPhone  = (s) => /^\+?\d{7,15}$/.test((s||"").trim());
const isEmail  = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s||"").trim());
const readMsg  = (e) => e?.response?.data?.detail || e?.message || "Something went wrong";

// singleton recaptcha
let recaptchaVerifier = null;
function getRecaptcha() {
  if (!recaptchaVerifier) {
    recaptchaVerifier = new RecaptchaVerifier(auth, "recaptcha-container", { size: "invisible" });
  }
  return recaptchaVerifier;
}

export default function LoginModern(){
  const [identifier, setIdentifier] = useState("");
  const [role, setRole] = useState(""); // ⬅️ force user to choose
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  // handle returning email link
  useEffect(()=>{
    (async ()=>{
      if (isSignInWithEmailLink(auth, window.location.href)) {
        let email = window.localStorage.getItem("emailForSignIn");
        let chosen = window.localStorage.getItem("emailForSignInRole") || "patient";
        if (!email) email = window.prompt("Confirm your email to finish sign-in:");
        try{
          setLoading(true);
          const cred = await signInWithEmailLink(auth, email, window.location.href);
          const idToken = await cred.user.getIdToken();
          const { data } = await api.post("/auth/firebase/login", {
            id_token: idToken,
            chosen_role: chosen,
            ensure_patient: chosen === "patient"
          });
          localStorage.setItem("auth", JSON.stringify({ token: data.token, role: data.role, email }));
          window.history.replaceState({}, document.title, "/login-modern");
          redirectByRole(data.role);
        }catch(e){
          setErr(readMsg(e));
        }finally{
          setLoading(false);
        }
      }
    })();
  },[]);

  function redirectByRole(r){
    if (r === "doctor")    window.location.href = "/doctor/patients";
    else if (r === "clinician") window.location.href = "/clinician/dashboard";
    else if (r === "admin")     window.location.href = "/admin";
    else                        window.location.href = "/patient/dashboard/me";
  }

  async function login(e){
    e?.preventDefault?.();
    setMsg(""); setErr("");

    const id = (identifier||"").trim();
    if (!id) { setErr("Enter your email or phone"); return; }

    try{
      setLoading(true);

      // email → send magic link
      if (isEmail(id)) {
        await sendSignInLinkToEmail(auth, id, actionCodeSettings);
        window.localStorage.setItem("emailForSignIn", id);
        window.localStorage.setItem("emailForSignInRole", role || "patient");
        setMsg("We sent you a sign-in link. Check your email.");
        setLoading(false);
        return;
      }

      // phone → OTP
      if (isPhone(id)) {
        const appVerifier = getRecaptcha();
        const confirmation = await signInWithPhoneNumber(auth, id, appVerifier);
        const code = window.prompt("Enter the SMS code");
        if (!code) { setLoading(false); return; }
        const cred = await confirmation.confirm(code);
        const token = await cred.user.getIdToken();
        const { data } = await api.post("/auth/firebase/login", {
          id_token: token,
          chosen_role: role || "patient",
          ensure_patient: (role || "patient") === "patient"
        });
        localStorage.setItem("auth", JSON.stringify({ token: data.token, role: data.role, phone: id }));
        redirectByRole(data.role);
        return;
      }

      setErr("Enter a valid email or phone (+country_code...).");
    }catch(e){
      setErr(readMsg(e));
    }finally{
      setLoading(false);
    }
  }

  async function googleLogin(){
    setMsg(""); setErr("");

    // ⬅️ NEW: Must choose a role before Google sign-in
    if (!role) {
      setErr("Please choose your role before continuing with Google.");
      return;
    }

    try{
      setLoading(true);
      const provider = new GoogleAuthProvider();
      const cred = await signInWithPopup(auth, provider);
      const idToken = await cred.user.getIdToken();
      const { data } = await api.post("/auth/firebase/login", {
        id_token: idToken,
        chosen_role: role,
        ensure_patient: role === "patient"
      });
      localStorage.setItem("auth", JSON.stringify({ token: data.token, role: data.role, email: cred.user.email || null }));
      redirectByRole(data.role);
    }catch(e){
      setErr(readMsg(e));
    }finally{
      setLoading(false);
    }
  }

  return (
    <Layout title="Login">
      <div style={{display:"flex", justifyContent:"center", padding:"24px"}}>
        <form className="auth-card" onSubmit={login} style={{margin:"0 auto"}}>
          <div className="h2">Welcome back</div>
          <div className="muted" style={{marginTop:6}}>
            Login with your <b>Email or Phone</b>, or use Google.
          </div>

          <input
            className="input"
            placeholder="Email or phone"
            value={identifier}
            onChange={(e)=>setIdentifier(e.target.value)}
          />

          {/* Role kept, but forced selection with a placeholder */}
          <select className="input" value={role} onChange={(e)=>setRole(e.target.value)}>
            <option value="" disabled>Choose role</option> {/* ⬅️ NEW placeholder */}
            <option value="patient">Patient</option>
            <option value="clinician">Clinician</option>
            <option value="doctor">Doctor</option>
            <option value="admin">Admin</option>
          </select>

          <button className="btn" type="submit" disabled={loading}>
            {loading ? "Please wait…" : "Continue"}
          </button>

          <div style={{height:8}} />
          <button className="btn secondary" type="button" onClick={googleLogin} disabled={loading}>
            Continue with Google
          </button>

          {/* reCAPTCHA v2 anchor (invisible) */}
          <div id="recaptcha-container" />

          {msg && <div style={{color:"#0E7ABF", marginTop:8}}>{msg}</div>}
          {err && <div style={{color:"crimson", marginTop:8}}>{err}</div>}

          <div style={{marginTop:12}}>
            Don’t have an account? <a href="/signup-modern">Sign up</a>
          </div>
        </form>
      </div>
    </Layout>
  );
}
