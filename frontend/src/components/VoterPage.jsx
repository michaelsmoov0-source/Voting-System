import React, { useEffect, useMemo, useState } from "react";
import { castVote, fetchResults, listCandidates, listElections } from "../api/voting";
import { encryptBallot } from "../utils/crypto";

const CountdownTimer = ({ targetTime, label, isActive }) => {
  const [timeLeft, setTimeLeft] = useState(null);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    if (!targetTime || !isActive) return;

    const calculateTimeLeft = () => {
      const now = new Date().getTime();
      const target = new Date(targetTime).getTime();
      const difference = target - now;

      if (difference > 0) {
        const days = Math.floor(difference / (1000 * 60 * 60 * 24));
        const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((difference % (1000 * 60)) / 1000);

        setTimeLeft({ days, hours, minutes, seconds });
        setIsExpired(false);
      } else {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        setIsExpired(true);
      }
    };

    calculateTimeLeft();
    const timer = setInterval(calculateTimeLeft, 1000);

    return () => clearInterval(timer);
  }, [targetTime, isActive]);

  if (!targetTime || !isActive) return null;

  const formatTime = (value) => value.toString().padStart(2, '0');

  return (
    <div className={`rounded-lg p-3 ${isExpired ? 'bg-red-50 border border-red-200' : 'bg-blue-50 border border-blue-200'}`}>
      <p className="text-sm font-medium text-slate-700 mb-1">{label}</p>
      {isExpired ? (
        <p className="text-red-600 font-semibold">Ended</p>
      ) : (
        <div className="flex gap-2 text-lg font-bold text-blue-600">
          {timeLeft?.days > 0 && (
            <div className="text-center">
              <div>{formatTime(timeLeft.days)}</div>
              <div className="text-xs font-normal">Days</div>
            </div>
          )}
          <div className="text-center">
            <div>{formatTime(timeLeft?.hours)}</div>
            <div className="text-xs font-normal">Hours</div>
          </div>
          <div className="text-center">
            <div>{formatTime(timeLeft?.minutes)}</div>
            <div className="text-xs font-normal">Minutes</div>
          </div>
          <div className="text-center">
            <div>{formatTime(timeLeft?.seconds)}</div>
            <div className="text-xs font-normal">Seconds</div>
          </div>
        </div>
      )}
    </div>
  );
};

const VoterPage = () => {
  const [elections, setElections] = useState([]);
  const [selectedElection, setSelectedElection] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [userId, setUserId] = useState("");
  const [matricNumber, setMatricNumber] = useState("");
  const [electionPassword, setElectionPassword] = useState("");
  const [status, setStatus] = useState("");
  const [results, setResults] = useState(null);
  const [isAnonymous, setIsAnonymous] = useState(false);

  const openElections = useMemo(
    () => elections.filter((election) => election.status === "open"),
    [elections]
  );

  const selectedElectionData = useMemo(
    () => elections.find((item) => String(item.id) === String(selectedElection)),
    [elections, selectedElection]
  );

  const isElectionActive = useMemo(() => {
    if (!selectedElectionData) return false;
    const now = new Date();
    const startTime = new Date(selectedElectionData.starts_at);
    const endTime = new Date(selectedElectionData.ends_at);
    return now >= startTime && now <= endTime;
  }, [selectedElectionData]);

  const electionStatus = useMemo(() => {
    if (!selectedElectionData) return null;
    const now = new Date();
    const startTime = new Date(selectedElectionData.starts_at);
    const endTime = new Date(selectedElectionData.ends_at);
    
    if (now < startTime) return { status: 'upcoming', label: 'Election Starts In:', color: 'blue' };
    if (now > endTime) return { status: 'ended', label: 'Election Ended:', color: 'red' };
    return { status: 'active', label: 'Election Ends In:', color: 'green' };
  }, [selectedElectionData]);

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

    if (!isElectionActive) {
      setStatus("Election is not active. You cannot vote at this time.");
      return;
    }

    try {
      const receipt = await castVote({
        election_id: Number(selectedElection),
        encrypted_ballot: await encryptBallot({
          publicKeyPem: selectedElectionData?.encryption_public_key,
          candidateId: Number(selectedCandidate),
        }),
        user_id: userId,
        matric_number: matricNumber,
        election_password: electionPassword,
        is_anonymous: isAnonymous,
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
      {selectedElectionData && electionStatus && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold text-slate-800">Election Status</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">{selectedElectionData.title}</h3>
              <p className="text-sm text-slate-600 mb-4">{selectedElectionData.description}</p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    electionStatus.status === 'active' ? 'bg-green-100 text-green-800' :
                    electionStatus.status === 'upcoming' ? 'bg-blue-100 text-blue-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {electionStatus.status === 'active' ? 'Active' :
                     electionStatus.status === 'upcoming' ? 'Upcoming' : 'Ended'}
                  </span>
                </div>
                <div className="text-sm text-slate-600">
                  <p>Starts: {new Date(selectedElectionData.starts_at).toLocaleString()}</p>
                  <p>Ends: {new Date(selectedElectionData.ends_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
            <div>
              {electionStatus.status === 'upcoming' && (
                <CountdownTimer 
                  targetTime={selectedElectionData.starts_at} 
                  label={electionStatus.label}
                  isActive={true}
                />
              )}
              {electionStatus.status === 'active' && (
                <CountdownTimer 
                  targetTime={selectedElectionData.ends_at} 
                  label={electionStatus.label}
                  isActive={true}
                />
              )}
              {electionStatus.status === 'ended' && (
                <div className="rounded-lg p-3 bg-red-50 border border-red-200">
                  <p className="text-sm font-medium text-slate-700 mb-1">Election Ended</p>
                  <p className="text-red-600 font-semibold">Voting is no longer available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
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
            User ID (optional)
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter your user ID"
            />
          </label>

          <label className="grid gap-2 text-sm font-medium text-slate-700">
            Matric Number (optional)
            <input
              className="rounded-lg border border-slate-300 px-3 py-2"
              value={matricNumber}
              onChange={(e) => setMatricNumber(e.target.value)}
              placeholder="Enter your matric number"
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
            className={`rounded-lg px-4 py-2 text-white transition ${
              isElectionActive 
                ? 'bg-brand-700 hover:bg-brand-500' 
                : 'bg-gray-400 cursor-not-allowed'
            }`}
            disabled={!isElectionActive}
          >
            {isElectionActive ? 'Submit Vote' : 'Election Not Active'}
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
