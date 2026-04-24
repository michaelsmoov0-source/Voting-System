import React from "react";
import ButtonLoader from "./ButtonLoader";

const MfaVerifyPage = ({ 
  mfaCode, 
  setMfaCode, 
  isMfaLoading, 
  handleMfaVerify, 
  status, 
  attemptsRemaining, 
  reverificationRequired, 
  showConfirmDialog, 
  setShowConfirmDialog, 
  handleReverification,
  handleGoToSetup,
  normalizeSixDigitCode, 
  handleCodePaste 
}) => {
  return (
    <div className="grid gap-3">
      {reverificationRequired && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          <strong>Reverification Required</strong><br />
          Too many failed attempts. A new MFA secret must be sent to your email.
        </div>
      )}

      <form className="grid gap-3" onSubmit={handleMfaVerify}>
        <input
          className="rounded-lg border border-slate-300 px-3 py-2"
          placeholder="6-digit MFA code"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          value={mfaCode}
          onChange={(e) => setMfaCode(normalizeSixDigitCode(e.target.value))}
          onPaste={handleCodePaste}
        />
        {attemptsRemaining !== null && attemptsRemaining < 4 && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {attemptsRemaining} attempts remaining
          </div>
        )}
        <ButtonLoader
          loading={isMfaLoading}
          loadingText="Verifying..."
          type="submit"
          className="w-full"
        >
          Verify MFA
        </ButtonLoader>
      </form>
      
      {/* Add option to go back to MFA setup */}
      {!reverificationRequired && (
        <div className="grid gap-3">
          <button
            className="rounded-lg bg-slate-600 px-4 py-2 text-white hover:bg-slate-500"
            onClick={handleGoToSetup}
          >
            Go Back to MFA Setup
          </button>
        </div>
      )}
      
      {reverificationRequired && (
        <div className="grid gap-3">
          <button
            className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-500"
            onClick={() => setShowConfirmDialog(true)}
          >
            Request Reverification
          </button>
        </div>
      )}

      {showConfirmDialog && (
        <div className="rounded-lg border border-slate-300 bg-slate-50 p-4">
          <h3 className="mb-2 font-semibold text-slate-800">
            Confirm Reverification
          </h3>
          <p className="mb-4 text-sm text-slate-600">
            Too many failed attempts. A new MFA secret must be sent to your email. You will need to configure MFA again. Continue?
          </p>
          <div className="flex gap-2">
            <button
              className="rounded-lg bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-500"
              onClick={handleReverification}
            >
              Yes, Send New Secret
            </button>
            <button
              className="rounded-lg bg-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-400"
              onClick={() => setShowConfirmDialog(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      
      {status && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-800">
          {status}
        </div>
      )}
    </div>
  );
};

export default MfaVerifyPage;
