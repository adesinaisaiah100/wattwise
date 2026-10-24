# Phase 09 — Local accounts and persistence

## Outcome

Let each household create an account and return to its saved appliance routines and analysis history on the same WattWise installation. Data stays in a local SQLite database; no cloud service is required.

## Implement

1. Registration with normalized unique email and a securely hashed password; login errors must not reveal whether an email exists.
2. Short-lived signed JWT sessions in HttpOnly, SameSite cookies for the browser. Logout clears the cookie. Signing secrets stay outside Git and persist locally across restarts.
3. SQLite schema and initialization for users, one saved appliance/routine profile per user, and analysis history with timestamps and JSON snapshots.
4. Authenticated account endpoints for reading/updating the appliance profile and listing a user's analysis history.
5. Associate new prepaid and postpaid results with the authenticated user. Users can access only their own profile and history.
6. Add register/login/logout/account pages with useful validation, session state, and clear disclosure that data is stored on this machine.
7. Use parameterized SQL, foreign keys, password hashing, token expiry/signature checks, bounded input sizes, safe error responses, and a bounded in-process login throttle. Never log passwords, JWTs, or bill bodies.
8. Provide a local data location, backup/reset instructions, and a warning that deleting the local database removes accounts and saved analyses.

## Components and links

- Depends on the existing Flask workflows and Phase 08 integration hardening.
- Adds account persistence to the currently stateless calculation endpoints without changing their calculation contracts.
- Phase 10 documents setup, local data handling, and the complete account-enabled demo.

## Verify and exit gate

**Status: Implementation and automated coverage are complete.** The test suite verifies registration/login/logout, scrypt password hashing, authenticated access, invalid/expired JWT rejection, login throttling, two-user isolation, and saved-data access after recreating the Flask app against temporary SQLite databases. Run the README smoke commands and manually verify the browser login after restarting the actual local server before the live demo.

- Register, log in, and log out through the browser; reject duplicate/invalid registration and wrong passwords safely.
- Verify password hashes are stored instead of plaintext and JWTs expire and reject invalid signatures.
- Save a household profile and analysis while logged in; restart Flask and confirm they remain available.
- Create two users and prove neither can read the other's household profile or history.
- Run the calculation journeys anonymously and while authenticated; calculations remain identical, while only authenticated requests persist user data.
- Run tests against temporary SQLite databases without touching the user's real local database.
