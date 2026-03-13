import { api, withAdminKey, withAuthToken } from "./client";

const adminHeaders = (token, adminKey) => {
  if (token) {
    return withAuthToken(token);
  }
  return withAdminKey(adminKey || "");
};

export const registerUser = async (payload) => (await api.post("/auth/register/", payload)).data;
export const loginUser = async (payload) => (await api.post("/auth/login/", payload)).data;
export const verifyAdminMFA = async (payload) => (await api.post("/auth/mfa/verify-login/", payload)).data;
export const reverifyAdminMFA = async (payload) => (await api.post("/auth/mfa/reverify/", payload)).data;
export const setupAdminMFA = async (token) => (await api.post("/auth/mfa/setup/", {}, withAuthToken(token))).data;
export const confirmAdminMFA = async (token, code) =>
  (await api.post("/auth/mfa/confirm/", { code }, withAuthToken(token))).data;
export const fetchDebugMfaCode = async (token, secret) =>
  (await api.post("/auth/mfa/debug-code/", { secret }, withAuthToken(token))).data;

export const listElections = async () => (await api.get("/elections/")).data;
export const listCandidates = async (electionId) =>
  (await api.get(`/candidates/?election_id=${electionId}`)).data;
export const castVote = async (payload) => (await api.post("/votes/cast/", payload)).data;
export const fetchResults = async (electionId) => (await api.get(`/elections/${electionId}/results/`)).data;

export const fetchAdminStats = async ({ token, adminKey }) =>
  (await api.get("/admin/dashboard/", adminHeaders(token, adminKey))).data;

export const createElection = async ({ token, adminKey }, payload) =>
  (await api.post("/elections/create/", payload, adminHeaders(token, adminKey))).data;

export const updateElection = async ({ token, adminKey }, electionId, payload) =>
  (await api.patch(`/elections/${electionId}/`, payload, adminHeaders(token, adminKey))).data;

export const deleteElection = async ({ token, adminKey }, electionId) =>
  (await api.delete(`/elections/${electionId}/`, adminHeaders(token, adminKey))).data;

export const createCandidate = async ({ token, adminKey }, payload) =>
  (await api.post("/candidates/create/", payload, adminHeaders(token, adminKey))).data;

export const deleteCandidate = async ({ token, adminKey }, candidateId) =>
  (await api.delete(`/candidates/${candidateId}/`, adminHeaders(token, adminKey))).data;

export const uploadCandidatePhoto = async ({ token, adminKey }, electionId, file) => {
  const formData = new FormData();
  formData.append("election_id", electionId);
  formData.append("image", file);
  return (await api.post("/candidates/upload-photo/", formData, adminHeaders(token, adminKey))).data;
};
