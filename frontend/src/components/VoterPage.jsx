import React, { useEffect, useMemo, useState } from "react";
import { castVote, fetchResults, listCandidates, listElections } from "../api/voting";
import { encryptBallot } from "../utils/crypto";

const VoterPage = () => {
  const [elections, setElections] = useState([]);
  const [selectedElection, setSelectedElection] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [voterId, setVoterId] = useState("");
  const [electionPassword, setElectionPassword] = useState("");
  const [status, setStatus] = useState("");
  const [results, setResults] = useState(null);

  const openElections = useMemo(
    () => elections.filter((election) => election.status === "open"),
    [elections]
  );

  const selectedElectionData = useMemo(
    () => elections.find((item) => String(item.id) === String(selectedElection)),
    [elections, selectedElection]
  );

  useEffect(() => {
    const load = async () => {
      const data = await listElections();
      setElections(data);
      const open = data.find((item) => item.status === "open");
      if (open) {
        setSelectedElection(String(open.id));
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!selectedElection) {
      setCandidates([]);
      setSelectedCandidate("");
      setElectionPassword("");
      return;
    }
    setElectionPassword("");
    const loadCandidates = async () => {
      const data = await listCandidates(selectedElection);
      setCandidates(data);
      setSelectedCandidate(data[0] ? String(data[0].id) : "");
    };
    loadCandidates();
  }, [selectedElection]);

  const submitVote = async (event) => {
    event.preventDefault();
    setStatus("");
    setResults(null);

    try {
      const receipt = await castVote({
        election_id: Number(selectedElection),
        encrypted_ballot: await encryptBallot({
          publicKeyPem: selectedElectionData?.encryption_public_key,
          candidateId: Number(selectedCandidate),
        }),
        voter_identifier: voterId,
        election_password: electionPassword,
      });
      setStatus(
        receipt.receipt_code
          ? `Vote submitted through mix-net. Receipt: ${receipt.receipt_code}`
          : receipt.detail || "Vote queued through mix-net."
      );
      const summary = await fetchResults(selectedElection);
      setResults(summary);
    } catch (error) {
      setStatus(error.response?.data?.detail || "Unable to submit vote.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Cast Your Vote</h2>
        <form className="grid gap-4" onSubmit={submitVote}>
          <label className="grid gap-2 text-sm font-medium text-slate-700">
            Election
            <select
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={selectedElection}
              onChange={(e) => setSelectedElection(e.target.value)}
            >
              <option value="">Select open election</option>
              {openElections.map((election) => (
                <option key={election.id} value={election.id}>
                  {election.title}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-700">
            Voter ID / Matric Number
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              required
              value={voterId}
              onChange={(e) => setVoterId(e.target.value)}
              placeholder="Enter your unique voter identifier"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-700">
            Candidate
            <select
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={selectedCandidate}
              onChange={(e) => setSelectedCandidate(e.target.value)}
            >
              <option value="">Select candidate</option>
              {candidates.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.full_name}
                </option>
              ))}
            </select>
          </label>
          {selectedElectionData?.requires_password && (
            <label className="grid gap-2 text-sm font-medium text-slate-700">
              Election Access Password
              <input
                type="password"
                className="rounded-lg border border-slate-300 px-3 py-2"
                required
                value={electionPassword}
                onChange={(e) => setElectionPassword(e.target.value)}
                placeholder="Enter election password"
              />
            </label>
          )}

          <button
            type="submit"
            className="rounded-lg bg-brand-700 px-4 py-2 text-white transition hover:bg-brand-500"
          >
            Submit Vote
          </button>
          {status && <p className="text-sm text-slate-700">{status}</p>}
        </form>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {candidates.map((candidate) => (
          <article key={candidate.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            {candidate.profile_image_url ? (
              <img
                src={candidate.profile_image_url}
                alt={candidate.full_name}
                className="h-52 w-full object-cover"
              />
            ) : (
              <div className="flex h-52 items-center justify-center bg-slate-100 text-slate-500">No image</div>
            )}
            <div className="space-y-2 p-4">
              <h3 className="text-lg font-semibold text-slate-800">{candidate.full_name}</h3>
              <p className="text-sm text-slate-600">{candidate.description}</p>
            </div>
          </article>
        ))}
      </div>

      {results && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-800">Current Tally: {results.election_title}</h3>
          <p className="mb-3 text-sm text-slate-600">Total votes: {results.total_votes}</p>
          <div className="space-y-2">
            {results.results.map((item) => (
              <p key={item.candidate_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {item.candidate_name}: {item.vote_count}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VoterPage;
