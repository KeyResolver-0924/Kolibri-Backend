CREATE TABLE public.housing_cooperatives (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  organisation_number text NOT NULL,
  name text NOT NULL,
  address text NOT NULL,
  city text NOT NULL,
  postal_code text NOT NULL,
  administrator_company text NULL,
  administrator_name text NOT NULL,
  administrator_person_number text NOT NULL,
  administrator_email text NOT NULL,
  created_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  CONSTRAINT housing_cooperatives_pkey PRIMARY KEY (id),
  CONSTRAINT housing_cooperatives_organisation_number_key UNIQUE (organisation_number)
);

CREATE TABLE public.mortgage_deeds (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  credit_number text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  housing_cooperative_id bigint NOT NULL,
  apartment_address text NOT NULL,
  apartment_postal_code text NOT NULL,
  apartment_city text NOT NULL,
  apartment_number text NOT NULL,
  status text NOT NULL DEFAULT 'CREATED'::text,
  bank_id bigint NOT NULL,
  created_by uuid NOT NULL,
  created_by_email text NOT NULL,  -- TODO: Later on we should have a user table with all app user details.
  CONSTRAINT mortgage_deeds_pkey PRIMARY KEY (id),
  CONSTRAINT unique_credit_number UNIQUE (credit_number),
  CONSTRAINT mortgage_deeds_housing_cooperative_id_fkey FOREIGN KEY (housing_cooperative_id) REFERENCES public.housing_cooperatives(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_mortgage_deeds_bank_id ON public.mortgage_deeds USING btree (bank_id);
CREATE INDEX IF NOT EXISTS idx_mortgage_deeds_housing_cooperative_id ON public.mortgage_deeds USING btree (housing_cooperative_id);

CREATE TABLE public.audit_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  deed_id bigint,
  entity_id bigint,                  -- Remove NOT NULL constraint to allow keeping logs after deletion
  action_type text NOT NULL,
  description text NOT NULL,
  timestamp timestamp with time zone NOT NULL DEFAULT now(),
  user_id uuid NOT NULL,
  CONSTRAINT audit_logs_pkey PRIMARY KEY (id),
  CONSTRAINT audit_logs_deed_id_fkey FOREIGN KEY (deed_id) REFERENCES public.mortgage_deeds(id) ON DELETE RESTRICT
  -- Intentionally no FK constraint on entity_id to preserve audit history
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_deed_id ON public.audit_logs USING btree (deed_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);

CREATE TABLE public.borrowers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  deed_id bigint NOT NULL,
  name text NOT NULL,
  person_number text NOT NULL,
  email text NOT NULL,
  ownership_percentage numeric NOT NULL,
  signature_timestamp timestamp with time zone NULL,
  CONSTRAINT borrowers_pkey PRIMARY KEY (id),
  CONSTRAINT borrowers_deed_id_fkey FOREIGN KEY (deed_id) REFERENCES public.mortgage_deeds(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_borrowers_deed_id ON public.borrowers USING btree (deed_id);

CREATE TABLE public.housing_cooperative_signers (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  mortgage_deed_id bigint NOT NULL,
  administrator_name text NOT NULL,
  administrator_person_number text NOT NULL,
  administrator_email text NOT NULL,
  signature_timestamp timestamp with time zone NULL,
  CONSTRAINT housing_cooperative_signers_pkey PRIMARY KEY (id),
  CONSTRAINT housing_cooperative_signers_mortgage_deed_id_fkey FOREIGN KEY (mortgage_deed_id) REFERENCES public.mortgage_deeds(id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_housing_cooperative_signers_mortgage_deed_id ON public.housing_cooperative_signers USING btree (mortgage_deed_id);

CREATE TABLE public.bank_users (
  id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL,
  name text NOT NULL,
  bank_id bigint NOT NULL,
  phone_number text,
  bank_name text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT bank_users_email_key UNIQUE (email)
);

-- Enable RLS on all tables
ALTER TABLE public.housing_cooperatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mortgage_deeds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.borrowers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.housing_cooperative_signers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bank_users ENABLE ROW LEVEL SECURITY;

-- Housing Cooperatives - Allow users to access their own cooperatives
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON public.housing_cooperatives;
CREATE POLICY "Users can access their own cooperatives" ON public.housing_cooperatives
  FOR ALL
  USING (auth.uid() = created_by)
  WITH CHECK (auth.uid() = created_by);

-- Mortgage Deeds - Special handling for bank users
CREATE POLICY "Allow bank users to access their own deeds" ON public.mortgage_deeds
  FOR ALL USING (
    CASE 
      WHEN (auth.jwt()->'raw_user_metadata'->>'bank_id') IS NOT NULL THEN 
        (auth.jwt()->'raw_user_metadata'->>'bank_id')::bigint = bank_id
      ELSE 
        auth.role() = 'authenticated'
    END
  );

-- Audit Logs - Allow all operations for authenticated users
CREATE POLICY "Allow all operations for authenticated users" ON public.audit_logs
  FOR ALL USING (auth.role() = 'authenticated');

-- Borrowers - Allow all operations for authenticated users
CREATE POLICY "Allow all operations for authenticated users" ON public.borrowers
  FOR ALL USING (auth.role() = 'authenticated');

-- Housing Cooperative Signers - Allow all operations for authenticated users
CREATE POLICY "Allow all operations for authenticated users" ON public.housing_cooperative_signers
  FOR ALL USING (auth.role() = 'authenticated');

-- Bank Users - RLS Policies
DROP POLICY IF EXISTS "Users can only access their own records" ON public.bank_users;
DROP POLICY IF EXISTS "Allow inserts during signup" ON public.bank_users;
DROP POLICY IF EXISTS "All users accept" ON public.bank_users;

CREATE POLICY "All users accept" 
ON public.bank_users
FOR ALL
TO public
USING (auth.uid() = id)
WITH CHECK (true);

CREATE TABLE public.mortgage_deeds (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  credit_number text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  housing_cooperative_id bigint NOT NULL,
  apartment_address text NOT NULL,
  apartment_postal_code text NOT NULL,
  apartment_city text NOT NULL,
  apartment_number text NOT NULL,
  status text NOT NULL DEFAULT 'CREATED'::text,
  bank_id bigint NOT NULL,
  created_by uuid NOT NULL,
  created_by_email text NOT NULL,  -- TODO: Later on we should have a user table with all app user details.
  CONSTRAINT mortgage_deeds_pkey PRIMARY KEY (id),
  CONSTRAINT unique_credit_number UNIQUE (credit_number),
  CONSTRAINT mortgage_deeds_housing_cooperative_id_fkey FOREIGN KEY (housing_cooperative_id) REFERENCES public.housing_cooperatives(id) ON DELETE RESTRICT
);
