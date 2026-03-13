import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Ensure error.response exists for consistent error handling
    if (!error.response) {
      error.response = {
        data: { detail: error.message || "Network error occurred" }
      };
    }
    return Promise.reject(error);
  }
);

export const withAdminKey = (adminKey) => ({
  headers: {
    "X-Admin-Key": adminKey,
  },
});

export const withAuthToken = (token) => ({
  headers: {
    Authorization: `Token ${token}`,
  },
});
