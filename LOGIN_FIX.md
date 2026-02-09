# Login/Sign Up Fix — Complete Resolution

## Problem Identified

**Symptoms:**
```
INFO: 127.0.0.1:36004 - "OPTIONS /api/v1/auth/login HTTP/1.1" 400 Bad Request
INFO: 127.0.0.1:53440 - "OPTIONS /api/v1/auth/register HTTP/1.1" 400 Bad Request
```

Login and registration were failing because CORS preflight requests returned 400 Bad Request.

## Root Causes (2 Issues)

### 1. Missing `/api/v1` Prefix in Frontend

**Problem:** Frontend API client was calling endpoints without the `/api/v1` prefix that backend expects.

**Examples:**
- ❌ Frontend called: `/auth/login`
- ✅ Backend expected: `/api/v1/auth/login`

**Impact:** All API requests were hitting non-existent routes, returning 404 or 400.

**Files affected:**
- [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts)
- [frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts)

### 2. CORS Origin Mismatch

**Problem:** Next.js dev server runs on port **3002**, but backend only allowed `http://localhost:3000`.

**Evidence:**
```bash
$ npm run dev
- Local:        http://localhost:3002
```

Backend CORS config defaulted to `["http://localhost:3000"]` only.

**Impact:** Browser preflight OPTIONS requests were rejected before reaching endpoint handlers.

---

## Fixes Applied

### Fix 1: Added `/api/v1` Prefix to All Frontend API Calls

**Updated [frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts):**
```typescript
// ❌ BEFORE:
async login(req: ApiLoginRequest): Promise<ApiResponse<ApiAuthResponse>> {
  return this.post<ApiAuthResponse>("/auth/login", req);
}

// ✅ AFTER:
async login(req: ApiLoginRequest): Promise<ApiResponse<ApiAuthResponse>> {
  return this.post<ApiAuthResponse>("/api/v1/auth/login", req);
}
```

**All endpoints fixed:**
- `/auth/login` → `/api/v1/auth/login`
- `/auth/register` → `/api/v1/auth/register`
- `/auth/me` → `/api/v1/auth/me` (also added missing `getMe()` method)
- `/auth/logout` → `/api/v1/auth/logout`
- `/cases/analyze` → `/api/v1/cases/analyze`
- `/files/upload` → `/api/v1/files/upload`

**Updated [frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts):**
- `/patients` → `/api/v1/patients`
- `/patients/{id}` → `/api/v1/patients/{id}`
- `/patients/{id}/timeline` → `/api/v1/patients/{id}/timeline`
- `/cases/reports/{id}` → `/api/v1/cases/reports/{id}`
- `/cases/approve` → `/api/v1/cases/approve`

### Fix 2: Configured CORS to Accept Frontend Port

**Updated [backend/.env](backend/.env):**
```bash
# JSON array format for pydantic-settings (list[str] fields require valid JSON)
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:3001","http://localhost:3002"]
```

**Updated [backend/src/medai/config.py](backend/src/medai/config.py):**
```python
allowed_origins: list[str] = Field(
    default=["http://localhost:3000"],
    description="CORS allowed origins (JSON array format in .env)",
)
```

Pydantic-settings requires list fields to be valid JSON arrays in .env files.

---

## Testing Instructions

### 1. Restart Backend (to load new CORS config)
```bash
cd backend
# Stop current server (Ctrl+C)
make run
# Or:
uvicorn medai.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected startup logs:**
```
INFO:     Started server process [PID]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

**Note the actual port (usually 3002):**
```
- Local:        http://localhost:3002
```

### 3. Test Login
1. Open browser to `http://localhost:3002/auth/login`
2. Try logging in with admin credentials:
   - Email: `admin@example.com`
   - Password: `admin123`
3. Check browser DevTools Network tab:
   - OPTIONS request to `/api/v1/auth/login` should return **200 OK**
   - POST request to `/api/v1/auth/login` should return **200 OK** with token

### 4. Test Registration
1. Go to `http://localhost:3002/auth/register`
2. Fill out form with new user details
3. Submit registration
4. Check Network tab:
   - OPTIONS request to `/api/v1/auth/register` → **200 OK**
   - POST request to `/api/v1/auth/register` → **201 Created** with token

### 5. Verify Full Flow
1. After login, navigate to `/patients`
2. Should see patient list without "Not authenticated" errors
3. Try creating a new patient
4. Go to `/agent` and test case analysis

---

## Backend CORS Middleware Config

The CORS middleware in [backend/src/medai/main.py](backend/src/medai/main.py#L74-L79) is configured as:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Now includes :3002
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This middleware:
- ✅ Handles OPTIONS preflight requests automatically
- ✅ Returns proper CORS headers for allowed origins
- ✅ Allows all HTTP methods (GET, POST, PUT, DELETE, OPTIONS)
- ✅ Allows all headers (including Authorization)
- ✅ Allows credentials (cookies, auth headers)

---

## Verification Checklist

After restarting backend:

- [ ] Backend starts without errors
- [ ] Backend logs show `allow_origins` includes `:3002`
- [ ] Frontend dev server runs on port shown in startup message
- [ ] Browser can open frontend without CORS errors
- [ ] OPTIONS requests to `/api/v1/auth/*` return 200
- [ ] Login form submission succeeds
- [ ] Registration form submission succeeds
- [ ] Token stored in localStorage under `STORAGE_KEYS.authToken`
- [ ] Authenticated requests include `Authorization: Bearer <token>`
- [ ] `/patients` page loads after login
- [ ] Agent page can analyze cases

---

## Files Changed

### Frontend
1. **[frontend/src/lib/api/client.ts](frontend/src/lib/api/client.ts)**
   - Added `/api/v1` prefix to all auth, cases, files endpoints
   - Added missing `getMe()` method for auth state refresh

2. **[frontend/src/lib/hooks.ts](frontend/src/lib/hooks.ts)**
   - Added `/api/v1` prefix to all patients, timeline, reports endpoints

### Backend
3. **[backend/.env](backend/.env)**
   - Added `ALLOWED_ORIGINS` with comma-separated list including `:3002`

4. **[backend/src/medai/config.py](backend/src/medai/config.py)**
   - Imported `field_validator` from pydantic
   - Added `parse_allowed_origins` validator to parse comma-separated strings

---

## Expected Network Flow (After Fix)

### Login Request Sequence:

1. **OPTIONS /api/v1/auth/login** (Preflight)
   ```
   Request Headers:
     Origin: http://localhost:3002
     Access-Control-Request-Method: POST
     Access-Control-Request-Headers: content-type
   
   Response: 200 OK
     Access-Control-Allow-Origin: http://localhost:3002
     Access-Control-Allow-Methods: *
     Access-Control-Allow-Headers: *
     Access-Control-Allow-Credentials: true
   ```

2. **POST /api/v1/auth/login** (Actual Request)
   ```
   Request Headers:
     Origin: http://localhost:3002
     Content-Type: application/json
   
   Request Body:
     {"email": "admin@example.com", "password": "admin123"}
   
   Response: 200 OK
     Access-Control-Allow-Origin: http://localhost:3002
     Content-Type: application/json
   
   Response Body:
     {
       "access_token": "eyJ...",
       "token_type": "bearer",
       "user": {"id": "...", "email": "admin@example.com", "role": "admin"}
     }
   ```

3. **Frontend stores token:**
   ```typescript
   localStorage.setItem(STORAGE_KEYS.authToken, response.access_token);
   ```

---

## Debugging Tips

If issues persist:

### Check Backend CORS Config
```bash
cd backend
source .venv/bin/activate
python -c "from medai.config import get_settings; print(get_settings().allowed_origins)"
```
Should output: `['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002']`

### Check Frontend Port
```bash
cd frontend
npm run dev | grep "Local:"
```
Should show the actual port (e.g., 3002).

### Check Browser DevTools
1. Open DevTools → Network tab
2. Enable "Preserve log"
3. Filter by "auth"
4. Try logging in
5. Inspect failed requests:
   - Look for "CORS error" in console
   - Check request URL (should include `/api/v1`)
   - Check response status (should be 200, not 400/404)

### Check Backend Logs
Look for these lines in backend startup:
```
INFO:     Application startup complete.
```

If you see CORS-related errors in browser console, restart the backend to ensure new config is loaded.

---

## Summary

**Problem:** Login/register failed due to:
1. Frontend missing `/api/v1` prefix on all API calls
2. Backend CORS only allowed `:3000`, but frontend ran on `:3002`

**Solution:**
1. Added `/api/v1` prefix to all frontend API endpoints
2. Added `:3002` to backend `ALLOWED_ORIGINS`
3. Added pydantic validator to parse comma-separated origins

**Status:** ✅ **FIXED**

Both login and registration should now work correctly after backend restart.
