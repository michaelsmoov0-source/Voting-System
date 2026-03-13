import React, { useEffect, useState } from "react";
import {
  createCandidate,
  createElection,
  deleteCandidate,
  deleteElection,
  fetchAdminStats,
  listCandidates,
  listElections,
  uploadCandidatePhoto,
  updateElection,
} from "../api/voting";

const AdminPage = ({ token, onMfaReverifyRequired }) => {
  const [adminKey, setAdminKey] = useState("");
  const [stats, setStats] = useState(null);
  const [elections, setElections] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [status, setStatus] = useState("");
  const [candidateImageFile, setCandidateImageFile] = useState(null);

  const [newElection, setNewElection] = useState({
    title: "",
    description: "",
    starts_at: "",
    ends_at: "",
    max_votes: "",
    access_password: "",
    status: "draft",
  });

  const [newCandidate, setNewCandidate] = useState({
    election: "",
    full_name: "",
    profile_image_url: "",
    description: "",
  });

  const loadData = async (key) => {
    const auth = { token, adminKey: key };
    const [statsData, electionsData] = await Promise.all([fetchAdminStats(auth), listElections()]);
    setStats(statsData);
    setElections(electionsData);

    if (electionsData[0]) {
      const activeElection = newCandidate.election || String(electionsData[0].id);
      setNewCandidate((prev) => ({ ...prev, election: activeElection }));
      const candidateData = await listCandidates(activeElection);
      setCandidates(candidateData);
    } else {
      setCandidates([]);
    }
  };

  useEffect(() => {
    if (!newCandidate.election) {
      return;
    }
    const loadCandidates = async () => {
      const data = await listCandidates(newCandidate.election);
      setCandidates(data);
    };
    loadCandidates();
  }, [newCandidate.election]);

  useEffect(() => {
    if (token) {
      loadData("");
    }
  }, [token]);

  const handleConnect = async () => {
    setStatus("");
    try {
      await loadData(adminKey);
      setStatus("Admin connected.");
    } catch (error) {
      const detail = error.response?.data?.detail || "Could not connect admin API.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  const handleCreateElection = async (event) => {
    event.preventDefault();
    setStatus("");
    try {
      const payload = {
        ...newElection,
        max_votes: newElection.max_votes ? Number(newElection.max_votes) : null,
      };
      await createElection({ token, adminKey }, payload);
      await loadData(adminKey);
      setStatus("Election created.");
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to create election.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  const handleStatusChange = async (electionId, statusValue) => {
    try {
      await updateElection({ token, adminKey }, electionId, { status: statusValue });
      await loadData(adminKey);
      setStatus("Election updated.");
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to update election.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  const handleDeleteElection = async (electionId) => {
    try {
      await deleteElection({ token, adminKey }, electionId);
      await loadData(adminKey);
      setStatus("Election deleted.");
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to delete election.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  const handleCreateCandidate = async (event) => {
    event.preventDefault();
    try {
      let profileImageUrl = newCandidate.profile_image_url;
      if (candidateImageFile) {
        const upload = await uploadCandidatePhoto(
          { token, adminKey },
          Number(newCandidate.election),
          candidateImageFile
        );
        profileImageUrl = upload.profile_image_url;
      }
      await createCandidate({ token, adminKey }, {
        ...newCandidate,
        profile_image_url: profileImageUrl,
        election: Number(newCandidate.election),
      });
      await loadData(adminKey);
      setStatus("Candidate created.");
      setNewCandidate((prev) => ({ ...prev, full_name: "", profile_image_url: "", description: "" }));
      setCandidateImageFile(null);
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to create candidate.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  const handleDeleteCandidate = async (candidateId) => {
    try {
      await deleteCandidate({ token, adminKey }, candidateId);
      await loadData(adminKey);
      setStatus("Candidate deleted.");
    } catch (error) {
      const detail = error.response?.data?.detail || "Failed to delete candidate.";
      if (String(detail).toLowerCase().includes("re-verification required")) {
        onMfaReverifyRequired?.(detail);
        return;
      }
      setStatus(detail);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Admin Panel</h2>
        <label className="grid gap-2 text-sm font-medium text-slate-700">
          {token ? "Fallback Admin API Key (optional)" : "Admin API Key"}
          <input
            type="password"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Enter ADMIN_API_KEY"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <button
          className="mt-3 rounded-lg bg-slate-800 px-4 py-2 text-white transition hover:bg-slate-700"
          onClick={handleConnect}
        >
          Connect
        </button>
        {status && <p className="mt-2 text-sm text-slate-700">{status}</p>}
      </div>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-slate-500">Elections</p>
            <p className="text-2xl font-semibold text-slate-800">{stats.elections}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-slate-500">Candidates</p>
            <p className="text-2xl font-semibold text-slate-800">{stats.candidates}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm text-slate-500">Total Votes</p>
            <p className="text-2xl font-semibold text-slate-800">{stats.total_votes}</p>
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Create Election</h3>
          <form className="grid gap-3" onSubmit={handleCreateElection}>
            <input
              required
              placeholder="Election title"
              value={newElection.title}
              onChange={(e) => setNewElection((prev) => ({ ...prev, title: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <textarea
              placeholder="Election description"
              value={newElection.description}
              onChange={(e) => setNewElection((prev) => ({ ...prev, description: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <label className="grid gap-2 text-sm font-medium text-slate-700">
              Start datetime (UTC)
              <input
                required
                type="datetime-local"
                value={newElection.starts_at}
                onChange={(e) => setNewElection((prev) => ({ ...prev, starts_at: e.target.value }))}
                className="rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="grid gap-2 text-sm font-medium text-slate-700">
              End datetime (UTC)
              <input
                required
                type="datetime-local"
                value={newElection.ends_at}
                onChange={(e) => setNewElection((prev) => ({ ...prev, ends_at: e.target.value }))}
                className="rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <input
              type="number"
              min="1"
              placeholder="Maximum votes (optional)"
              value={newElection.max_votes}
              onChange={(e) => setNewElection((prev) => ({ ...prev, max_votes: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <input
              type="password"
              placeholder="Election access password (optional)"
              value={newElection.access_password}
              onChange={(e) => setNewElection((prev) => ({ ...prev, access_password: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <select
              value={newElection.status}
              onChange={(e) => setNewElection((prev) => ({ ...prev, status: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="draft">Draft</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
            <button type="submit" className="rounded-lg bg-brand-700 px-4 py-2 text-white hover:bg-brand-500">
              Create Election
            </button>
          </form>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Create Candidate</h3>
          <form className="grid gap-3" onSubmit={handleCreateCandidate}>
            <select
              required
              value={newCandidate.election}
              onChange={(e) => setNewCandidate((prev) => ({ ...prev, election: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">Select election</option>
              {elections.map((election) => (
                <option key={election.id} value={election.id}>
                  {election.title}
                </option>
              ))}
            </select>
            <input
              required
              placeholder="Candidate full name"
              value={newCandidate.full_name}
              onChange={(e) => setNewCandidate((prev) => ({ ...prev, full_name: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <input
              placeholder="Profile image URL"
              value={newCandidate.profile_image_url}
              onChange={(e) => setNewCandidate((prev) => ({ ...prev, profile_image_url: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <label className="grid gap-2 text-sm font-medium text-slate-700">
              Or upload candidate photo
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setCandidateImageFile(e.target.files?.[0] || null)}
                className="rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <textarea
              required
              placeholder="Candidate description / manifesto"
              value={newCandidate.description}
              onChange={(e) => setNewCandidate((prev) => ({ ...prev, description: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
            <button type="submit" className="rounded-lg bg-brand-700 px-4 py-2 text-white hover:bg-brand-500">
              Create Candidate
            </button>
          </form>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Manage Elections</h3>
          <div className="space-y-3">
            {elections.map((election) => (
              <div key={election.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-800">{election.title}</p>
                <p className="mb-2 text-sm text-slate-600">{election.description}</p>
                <div className="flex gap-2">
                  <select
                    value={election.status}
                    onChange={(e) => handleStatusChange(election.id, e.target.value)}
                    className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
                  >
                    <option value="draft">Draft</option>
                    <option value="open">Open</option>
                    <option value="closed">Closed</option>
                  </select>
                  <button
                    onClick={() => handleDeleteElection(election.id)}
                    className="rounded-lg bg-orange-700 px-3 py-1 text-sm text-white hover:bg-orange-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-800">Candidate List</h3>
          <div className="space-y-3">
            {candidates.map((candidate) => (
              <div key={candidate.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="font-semibold text-slate-800">{candidate.full_name}</p>
                <p className="text-sm text-slate-600">{candidate.description}</p>
                <p className="mb-2 text-xs text-slate-500">{candidate.profile_image_url || "No image URL"}</p>
                <button
                  onClick={() => handleDeleteCandidate(candidate.id)}
                  className="rounded-lg bg-orange-700 px-3 py-1 text-sm text-white hover:bg-orange-600"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
