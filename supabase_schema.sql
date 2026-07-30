-- Run this in Supabase SQL editor before deploying the app.
create table if not exists public.crm_state (
    id text primary key,
    payload jsonb not null,
    updated_at timestamptz not null default timezone('utc', now())
);

alter table public.crm_state enable row level security;

-- Policy for server-side key usage from Streamlit secrets.
-- If you use ANON key instead, create stricter policies as needed.
drop policy if exists "crm_state_service_rw" on public.crm_state;

create policy "crm_state_service_rw"
on public.crm_state
for all
using (true)
with check (true);
