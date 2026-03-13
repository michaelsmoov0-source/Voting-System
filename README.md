# Voting System

Stack:
- Frontend: Vite + React + Tailwind CSS
- Backend: Django + DRF
- Database: Supabase Postgres

## Backend
1. `pip install -r requirements.txt`
2. Create `backend/.env` from `backend/.env.example`
3. `cd backend`
4. `python manage.py migrate`
5. `python manage.py createsuperuser`
6. `python manage.py runserver`

## Frontend
1. `cd frontend`
2. Create `.env` from `.env.example`
3. `npm install`
4. `npm run dev`

## Notes
- Auth endpoints are available at `/api/auth/*` (register, login, MFA setup/verify).
- Admin users must complete MFA before admin login is finalized.
- Admin registration now requires email, and MFA secret is sent to that email during setup.
- MFA codes are configured to expire every 1 hour (`MFA_CODE_INTERVAL_SECONDS=3600`).
- Voting now encrypts ballot content in React (Web Crypto RSA-OAEP) before submit.
- Backend applies a mix-net shuffle before encrypted ballots are persisted to `Vote`.
- Candidate data is purged 2 days after election end (`CANDIDATE_RETENTION_DAYS`), while election metadata and archived result snapshots are kept for review.
- Candidate image upload endpoint stores photos in Supabase Storage bucket (`SUPABASE_BUCKET_NAME`).
- You can run manual cleanup with `python manage.py purge_candidate_data`.
- Elections support optional vote limit (`max_votes`) and optional access password (`access_password`).
- Candidate records support `profile_image_url` and `description`.








sk-ws-01-TJ64zvVTQG7Rdk2IR32bheN1gx58qsAX-zGUBuKMaEAt7Gg35K0KbBGT8Da03r2stz58Rh9cN492ZPuTvDFW0TK_DvIKVA