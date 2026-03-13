import React, { useState } from "react";
import AdminPage from "./components/AdminPage";
import AuthPage from "./components/AuthPage";
import VoterPage from "./components/VoterPage";

const App = () => {
  const [activeTab, setActiveTab] = useState("voter");
  const [session, setSession] = useState(null);
  const [authNotice, setAuthNotice] = useState("");

  const isAdmin = Boolean(session?.is_admin);

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-200 px-4 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-800">Secure Electronic Voting System</h1>
              <p className="text-sm text-slate-600">
                React + Django + Supabase with candidate profile pictures and descriptions.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  activeTab === "voter"
                    ? "bg-brand-700 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
                onClick={() => setActiveTab("voter")}
              >
                Voter Portal
              </button>
              {isAdmin && (
                <button
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                    activeTab === "admin"
                      ? "bg-brand-700 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                  onClick={() => setActiveTab("admin")}
                >
                  Admin Portal
                </button>
              )}
              {session ? (
                <button
                  className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
                  onClick={() => setSession(null)}
                >
                  Logout ({session.username})
                </button>
              ) : (
                <button
                  className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                    activeTab === "auth"
                      ? "bg-brand-700 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                  onClick={() => setActiveTab("auth")}
                >
                  Login / Register
                </button>
              )}
            </div>
          </div>
        </header>
        {activeTab === "voter" && <VoterPage />}
        {activeTab === "auth" && (
          <AuthPage
            onAuthenticated={(authSession) => {
              setSession(authSession);
              setAuthNotice("");
            }}
            notice={authNotice}
          />
        )}
        {activeTab === "admin" && isAdmin && (
          <AdminPage
            token={session?.token}
            onMfaReverifyRequired={(detail) => {
              setSession(null);
              setAuthNotice(detail || "Admin MFA re-verification required.");
              setActiveTab("auth");
            }}
          />
        )}
      </div>
    </main>
  );
};

export default App;
