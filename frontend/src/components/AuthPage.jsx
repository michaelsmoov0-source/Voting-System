import React, { useState } from "react";
import {
  confirmAdminMFA,
  fetchDebugMfaCode,
  getSetupToken,
  loginUser,
  registerUser,
  reverifyAdminMFA,
  requestNewMfaCode,
  setupAdminMFA,
  verifyAdminMFA,
} from "../api/voting";
import Loader from "./Loader";
import ButtonLoader from "./ButtonLoader";
import LoadingOverlay from "./LoadingOverlay";
import LoginPage from "./LoginPage";
import MfaVerifyPage from "./MfaVerifyPage";
import MfaSetupPage from "./MfaSetupPage";

const AuthPage = ({ onAuthenticated, notice = "" }) => {
  const [mode, setMode] = useState("login");
  const [status, setStatus] = useState("");
  const [preauthToken, setPreauthToken] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [mfaSecretInput, setMfaSecretInput] = useState("");
  const [debugCode, setDebugCode] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [attemptsRemaining, setAttemptsRemaining] = useState(null);
  const [reverificationRequired, setReverificationRequired] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  
  // Loading states
  const [isLoginLoading, setIsLoginLoading] = useState(false);
  const [isRegisterLoading, setIsRegisterLoading] = useState(false);
  const [isMfaLoading, setIsMfaLoading] = useState(false);
  const [isSetupLoading, setIsSetupLoading] = useState(false);
  const [globalLoading, setGlobalLoading] = useState(false);

  const [loginPayload, setLoginPayload] = useState({ 
    username: "", 
    password: "" 
  });
  const [registerPayload, setRegisterPayload] = useState({
    username: "",
    email: "",
    password: "",
    role: "voter",
    admin_invite_key: "",
  });

  const extractErrorMessage = (error, fallback) => {
    const data = error?.response?.data;
    if (!data) {
      return fallback;
    }
    
    // Handle string responses
    if (typeof data === "string") {
      return data;
    }
    
    // Handle detail field (common in DRF responses)
    if (data.detail) {
      return data.detail;
    }
    
    // Handle non_field_errors (common in DRF serializer validation)
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(" ");
    }
    
    // Handle field validation errors
    if (typeof data === "object") {
      const fieldErrors = Object.entries(data)
        .map(([field, value]) => {
          if (Array.isArray(value)) {
            return `${field}: ${value.join(" ")}`;
          }
          return `${field}: ${String(value)}`;
        })
        .join(" | ");
      
      if (fieldErrors) {
        return fieldErrors;
      }
    }
    
    // Fallback to stringifying the entire response if it's an object
    if (typeof data === "object") {
      try {
        return JSON.stringify(data);
      } catch {
        return fallback;
      }
    }
    
    return fallback;
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setStatus("");
    setIsRegisterLoading(true);
    try {
      const data = await registerUser(registerPayload);
      onAuthenticated(data);
      setStatus("Registration successful.");
    } catch (error) {
      setStatus(extractErrorMessage(error, "Registration failed."));
    } finally {
      setIsRegisterLoading(false);
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setStatus("");
    setIsLoginLoading(true);
    try {
      const data = await loginUser(loginPayload);
      if (data.mfa_required) {
        setPreauthToken(data.preauth_token);
        setMode("mfa-verify");
        setStatus("Enter your MFA code to complete admin login.");
        return;
      }
      onAuthenticated(data);
      setStatus("Login successful.");
    } catch (error) {
      const payload = error.response?.data;
      if (payload?.mfa_setup_required && payload?.setup_token) {
        setSetupToken(payload.setup_token);
        setMode("mfa-setup");
        setStatus(payload.detail || "Set up MFA for admin account.");
        return;
      }
      setStatus(extractErrorMessage(error, "Login failed."));
    } finally {
      setIsLoginLoading(false);
    }
  };

  const handleMfaVerify = async (event) => {
    event.preventDefault();
    setStatus("");
    setAttemptsRemaining(null);
    setReverificationRequired(false);
    setIsMfaLoading(true);
    
    try {
      const data = await verifyAdminMFA({ preauth_token: preauthToken, code: mfaCode });
      onAuthenticated(data);
      setStatus("Admin MFA verified.");
    } catch (error) {
      const response = error.response?.data;
      if (response?.reverification_required) {
        setReverificationRequired(true);
        setAttemptsRemaining(0);
        setStatus("Too many failed attempts. Please request reverification.");
      } else if (response?.attempts_remaining !== undefined) {
        setAttemptsRemaining(response.attempts_remaining);
        setStatus(response.detail || "MFA verification failed.");
      } else {
        setStatus(extractErrorMessage(error, "MFA verification failed."));
      }
    } finally {
      setIsMfaLoading(false);
    }
  };

  const handleGoToSetup = async () => {
    if (preauthToken) {
      setGlobalLoading(true);
      try {
        const data = await getSetupToken({ preauth_token: preauthToken });
        console.log("getSetupToken response:", data);
        if (data.setup_token) {
          setSetupToken(data.setup_token);
          setMode("mfa-setup");
          setMfaCode("");
          setDebugCode("");
          setStatus(data.detail || "Setup token generated. Proceed to MFA setup.");
        }
      } catch (error) {
        console.error("getSetupToken error:", error);
        setStatus(extractErrorMessage(error, "Failed to get setup token."));
      } finally {
        setGlobalLoading(false);
      }
    } else {
      console.log("No preauthToken available");
      setStatus("No valid session found. Please login again.");
    }
  };

  const handleReverification = async () => {
    setStatus("");
    setShowConfirmDialog(false);
    setGlobalLoading(true);
    
    try {
      if (reverificationRequired) {
        // Handle reverification due to failed attempts
        const data = await reverifyAdminMFA({ preauth_token: preauthToken });
        
        if (data.setup_required && data.setup_token) {
          // New secret sent, go to MFA setup
          setSetupToken(data.setup_token);
          setMode("mfa-setup");
          setMfaCode("");
          setDebugCode("");
          setReverificationRequired(false);
          setAttemptsRemaining(null);
          setStatus(data.detail || "New MFA secret sent. Please complete MFA setup again.");
        } else {
          // Fallback - shouldn't happen with new backend logic
          setStatus("Unexpected response from server. Please try again.");
        }
      } else {
        // Handle request for new MFA code
        const data = await requestNewMfaCode({ preauth_token: preauthToken });
        setStatus(data.detail || "New MFA code sent to your email.");
        setMfaCode("");
      }
    } catch (error) {
      setStatus(extractErrorMessage(error, "Request failed."));
    } finally {
      setGlobalLoading(false);
    }
  };

  const normalizeSixDigitCode = (value) => value.replace(/\D/g, "").slice(0, 6);
  const handleCodePaste = (event) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData("text");
    setMfaCode(normalizeSixDigitCode(pasted));
  };

  const handleMfaSetup = async () => {
    setStatus("");
    setDebugCode("");
    setIsSetupLoading(true);
    try {
      const data = await setupAdminMFA(setupToken);
      
      if (data.debug_secret) {
        setDebugCode(data.debug_secret);
        setStatus(
          `DEBUG MODE: MFA Secret is ${data.debug_secret}. Use this in your authenticator app or paste below for debug code.`
        );
      } else {
        setStatus(
          data.detail ||
            "MFA secret sent to your email. Add it in your authenticator app."
        );
      }
    } catch (error) {
      setStatus(extractErrorMessage(error, "MFA setup failed."));
    } finally {
      setIsSetupLoading(false);
    }
  };

  const handleMfaConfirm = async (event) => {
    event.preventDefault();
    setStatus("");
    setIsMfaLoading(true);
    try {
      await confirmAdminMFA(setupToken, mfaCode);
      setMode("login");
      setMfaCode("");
      setStatus("MFA enabled. Now login again.");
    } catch (error) {
      setStatus(extractErrorMessage(error, "MFA confirmation failed."));
    } finally {
      setIsMfaLoading(false);
    }
  };

  const handleFetchDebugCode = async () => {
    setStatus("");
    setIsSetupLoading(true);
    try {
      const data = await fetchDebugMfaCode(setupToken, mfaSecretInput);
      if (data.debug_current_code) {
        setDebugCode(data.debug_current_code);
        setMfaCode(data.debug_current_code);
        setStatus("Debug code fetched and autofilled.");
      }
    } catch (error) {
      setStatus(extractErrorMessage(error, "Could not fetch debug MFA code."));
    } finally {
      setIsSetupLoading(false);
    }
  };

  return (
    <>
      <LoadingOverlay show={globalLoading} text="Processing..." />
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Account Access</h2>
        {(notice || status) && (
          <p className="mb-4 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">
            {notice || status}
          </p>
        )}

      {(mode === "login" || mode === "register") && (
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => setMode("login")}
            className={`rounded-lg px-3 py-2 text-sm ${mode === "login" ? "bg-brand-700 text-white" : "bg-slate-100"}`}
          >
            Login
          </button>
          <button
            onClick={() => setMode("register")}
            className={`rounded-lg px-3 py-2 text-sm ${mode === "register" ? "bg-brand-700 text-white" : "bg-slate-100"}`}
          >
            Register
          </button>
        </div>
      )}

      {mode === "login" && (
        <LoginPage 
          loginPayload={loginPayload}
          setLoginPayload={setLoginPayload}
          isLoginLoading={isLoginLoading}
          handleLogin={handleLogin}
          status={status}
        />
      )}

      {mode === "register" && (
        <form className="grid gap-3" onSubmit={handleRegister}>
          <input
            className="rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Username (User ID, Matric Number, or any username)"
            value={registerPayload.username}
            onChange={(e) => setRegisterPayload((prev) => ({ ...prev, username: e.target.value }))}
          />
          <input
            className="rounded-lg border border-slate-300 px-3 py-2"
            placeholder={registerPayload.role === "admin" ? "Email (required for admin)" : "Email (optional)"}
            required={registerPayload.role === "admin"}
            value={registerPayload.email}
            onChange={(e) => setRegisterPayload((prev) => ({ ...prev, email: e.target.value }))}
          />
          <input
            type="password"
            className="rounded-lg border border-slate-300 px-3 py-2"
            placeholder="Password"
            value={registerPayload.password}
            onChange={(e) => setRegisterPayload((prev) => ({ ...prev, password: e.target.value }))}
          />
          <select
            className="rounded-lg border border-slate-300 px-3 py-2"
            value={registerPayload.role}
            onChange={(e) => setRegisterPayload((prev) => ({ ...prev, role: e.target.value }))}
          >
            <option value="voter">Voter</option>
            <option value="admin">Admin</option>
          </select>
          {registerPayload.role === "admin" && (
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              placeholder="Admin invite key"
              value={registerPayload.admin_invite_key}
              onChange={(e) => setRegisterPayload((prev) => ({ ...prev, admin_invite_key: e.target.value }))}
            />
          )}
          <ButtonLoader 
            loading={isRegisterLoading}
            loadingText="Registering..."
            type="submit"
            className="w-full"
          >
            Register
          </ButtonLoader>
        </form>
      )}

      {mode === "mfa-verify" && (
        <MfaVerifyPage 
          mfaCode={mfaCode}
          setMfaCode={setMfaCode}
          isMfaLoading={isMfaLoading}
          handleMfaVerify={handleMfaVerify}
          status={status}
          attemptsRemaining={attemptsRemaining}
          reverificationRequired={reverificationRequired}
          showConfirmDialog={showConfirmDialog}
          setShowConfirmDialog={setShowConfirmDialog}
          handleReverification={handleReverification}
          handleGoToSetup={handleGoToSetup}
          normalizeSixDigitCode={normalizeSixDigitCode}
          handleCodePaste={handleCodePaste}
        />
      )}

      {mode === "mfa-setup" && (
        <MfaSetupPage 
          mfaSecretInput={mfaSecretInput}
          setMfaSecretInput={setMfaSecretInput}
          debugCode={debugCode}
          setDebugCode={setDebugCode}
          isSetupLoading={isSetupLoading}
          handleMfaSetup={handleMfaSetup}
          handleMfaConfirm={handleMfaConfirm}
          handleFetchDebugCode={handleFetchDebugCode}
          status={status}
        />
      )}
    </div>
    </>
  );
};

export default AuthPage;
