import React from "react";
import ButtonLoader from "./ButtonLoader";

const MfaSetupPage = ({ 
  mfaSecretInput, 
  setMfaSecretInput, 
  debugCode, 
  setDebugCode, 
  isSetupLoading, 
  handleMfaSetup, 
  handleMfaConfirm, 
  handleFetchDebugCode, 
  status 
}) => {
  return (
    <div className="grid gap-3">
      <ButtonLoader 
        loading={isSetupLoading}
        loadingText="Sending..."
        onClick={handleMfaSetup}
        className="w-full"
      >
        Send MFA Secret to Email
      </ButtonLoader>
      <input
        className="rounded-lg border border-slate-300 px-3 py-2"
        placeholder="Paste MFA secret from email"
        value={mfaSecretInput}
        onChange={(e) => setMfaSecretInput(e.target.value)}
      />
      
      <ButtonLoader 
        loading={isSetupLoading}
        loadingText="Fetching..."
        onClick={handleFetchDebugCode}
        disabled={!mfaSecretInput.trim()}
        className="w-full"
      >
        Fetch Debug 6-Digit Code
      </ButtonLoader>
      
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        <strong>DEBUG MODE:</strong> Enter the MFA secret from email above, then click "Fetch Debug Code" to get a 6-digit code for testing.
      </div>

      {debugCode && (
        <div className="rounded-lg border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-800">
          <strong>Debug Code:</strong> {debugCode}<br />
          Use this code to verify MFA setup.
        </div>
      )}

      <form className="grid gap-3" onSubmit={handleMfaConfirm}>
        <input
          className="rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Enter 6-digit MFA code"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          value={debugCode || ""}
          onChange={(e) => setDebugCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        />
        <ButtonLoader 
          loading={isSetupLoading}
          loadingText="Confirming..."
          type="submit"
          className="w-full"
        >
          Confirm MFA Setup
        </ButtonLoader>
      </form>
      
      {status && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-800">
          {status}
        </div>
      )}
    </div>
  );
};

export default MfaSetupPage;
