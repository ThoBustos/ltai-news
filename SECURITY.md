# Security

This document explains the security architecture and Row Level Security (RLS) implementation for the LTAI News project.

---

## Architecture Overview

This application uses Supabase as a backend with both server-side (Python) and client-side (frontend) access. Understanding the security model is critical.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (UNTRUSTED)                         │
│                                                                 │
│   React App ──► Supabase JS Client ──► anon key (public)       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase Edge                                │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Row Level Security (RLS)                   │   │
│   │                                                         │   │
│   │  Policy: "daily_digests" → SELECT only (public read)   │   │
│   │  Policy: "subscribers"   → No public access            │   │
│   │  Policy: "channels"      → No public access            │   │
│   │  Policy: "videos"        → No public access            │   │
│   └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                          │
└─────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    Backend (TRUSTED)                            │
│                                                                 │
│   Python Services ──► Supabase Client ──► service_role key     │
│                                           (bypasses RLS)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                            ▼
                    [Full database access]
```

---

## The CS Lesson: Authentication ≠ Authorization

| Concept | Definition | In Supabase |
|---------|-----------|-------------|
| **Authentication** | Proving who you are | The API key (anon or service_role) |
| **Authorization** | What you're allowed to do | Row Level Security (RLS) policies |

> **Key insight:** The `anon` key provides weak authentication (it's public), but RLS provides strong authorization. Security comes from the policies, not the key.

---

## Understanding RLS (Row Level Security)

**RLS is PostgreSQL's way of saying:** *"Even with a valid key, you can only do what the policies allow."*

```
┌──────────────────────────────────────────────────────────────┐
│ WITHOUT RLS (dangerous!)                                     │
│                                                              │
│   anon key ──────────────────────────► Full table access     │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ WITH RLS (secure)                                            │
│                                                              │
│   anon key ───► Policy Check ───► Only allowed operations    │
│                     │                                        │
│                     └──► "Can SELECT daily_digests"          │
│                          "Cannot SELECT subscribers"         │
│                          "Cannot DELETE anything"            │
│                          "Cannot UPDATE anything"            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Why This Matters: "Public Website" vs "Public Database Access"

| Concept | What It Means |
|---------|---------------|
| **Public Website** | Anyone can visit your site and see the UI you designed |
| **Public Database Access** | Anyone can query your database directly, bypassing your UI |

Without RLS, an attacker could open browser DevTools, copy your anon key, and:

```javascript
// An attacker in their own browser console:
const sb = createClient('your-url', 'your-anon-key-they-copied')

// Steal all subscriber emails
const { data } = await sb.from('subscribers').select('*')

// Delete all your content
await sb.from('daily_digests').delete().neq('id', 0)
```

**With RLS enabled:** These operations would fail with "permission denied".

---

## RLS Policy Summary (This Project)

| Table | Public (anon key) | Backend (service_role) |
|-------|-------------------|------------------------|
| `daily_digests` | ✅ SELECT only | ✅ Full access |
| `channels` | ❌ No access | ✅ Full access |
| `videos` | ❌ No access | ✅ Full access |
| `video_transcripts` | ❌ No access | ✅ Full access |
| `video_processed_data` | ❌ No access | ✅ Full access |
| `digest_references` | ❌ No access | ✅ Full access |
| `subscribers` | ❌ No access | ✅ Full access |

**What this means:**
- ✅ **Safe:** Anyone can read published digest content (intended behavior for the frontend)
- ✅ **Protected:** No one can modify data via the anon key
- ✅ **Secure:** Sensitive data (subscribers, video analysis) is not accessible from the client

---

## The Two Keys

| Key | Purpose | Visibility | RLS |
|-----|---------|------------|-----|
| `anon` (public) | Frontend/client-side access | Exposed in browser | ✅ Enforced |
| `service_role` | Backend/server-side access | Secret, never exposed | ❌ Bypassed |

```bash
# Frontend (.env) - OK to be in browser bundle
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...

# Backend (.env) - NEVER expose this
SUPABASE_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6...  # This is service_role
```

---

## Defense in Depth

```
Layer 1: Client-side         ❌ None (anyone can modify JS)
Layer 2: Transport           ✅ HTTPS (handled by Supabase)
Layer 3: API key             ⚠️ Public key = identity, not security
Layer 4: RLS policies        ✅ YOUR REAL SECURITY BOUNDARY
Layer 5: Database constraints ✅ Last line of defense (NOT NULL, FK, etc.)
```

> **Never trust the client.** All security must be enforced server-side (RLS in this case).

---

## For Contributors: Adding New Tables

When adding new tables to the database:

1. **Always enable RLS** before adding any data:
   ```sql
   ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
   ```

2. **Create explicit policies** for each allowed operation:
   ```sql
   -- Service role only (most tables)
   CREATE POLICY "new_table_service_only" ON new_table
       FOR ALL USING (auth.role() = 'service_role');
   
   -- If public read is needed
   CREATE POLICY "new_table_public_read" ON new_table
       FOR SELECT USING (true);
   ```

3. **Default deny** - no policy = no access (this is good!)

4. **Test with anon key** - verify you can only do what's intended:
   ```sql
   -- Check RLS is enabled
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
   
   -- Check policies exist
   SELECT tablename, policyname, cmd FROM pg_policies WHERE schemaname = 'public';
   ```

---

## Migration Reference

RLS policies are defined in: `supabase/migrations/20260101000000_enable_rls_policies.sql`

---

## Quick Reference: Verification Queries

Run these in Supabase SQL Editor to verify security is properly configured:

```sql
-- 1. Check RLS is enabled on all tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- 2. Check all policies exist
SELECT tablename, policyname, cmd 
FROM pg_policies 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- 3. Expected results:
-- All tables should show rowsecurity = true
-- daily_digests should have both public_read (SELECT) and service_all (ALL)
-- All other tables should only have service_only (ALL)
```

