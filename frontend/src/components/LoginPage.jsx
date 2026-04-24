import React from "react";
import ButtonLoader from "./ButtonLoader";

const LoginPage = ({ 
  loginPayload, 
  setLoginPayload, 
  isLoginLoading, 
  handleLogin, 
  status 
}) => {
  return (
    <div className="grid gap-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Username
        </label>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Enter username"
          value={loginPayload.username}
          onChange={(e) => setLoginPayload({ ...loginPayload, username: e.target.value })}
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          Password
        </label>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          type="password"
          placeholder="Enter password"
          value={loginPayload.password}
          onChange={(e) => setLoginPayload({ ...loginPayload, password: e.target.value })}
        />
      </div>
      {status && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {status}
        </div>
      )}
      <ButtonLoader
        loading={isLoginLoading}
        loadingText="Logging in..."
        onClick={handleLogin}
        className="w-full"
      >
        Login
      </ButtonLoader>
    </div>
  );
};

export default LoginPage;
