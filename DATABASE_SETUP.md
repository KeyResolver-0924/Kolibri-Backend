# Database Setup Guide

## Problem
The `signing_tokens` table doesn't exist in your Supabase database, which is causing the 404 error when trying to create signing tokens.

## Solution
You need to create the `signing_tokens` table in your Supabase database. Here are the steps:

### Option 1: Using Supabase Dashboard (Recommended)

1. **Go to your Supabase Dashboard**
   - Navigate to your project at https://supabase.com/dashboard
   - Select your project

2. **Open the SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Run the following SQL commands**

```sql
-- Create the signing_tokens table
CREATE TABLE IF NOT EXISTS public.signing_tokens (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  deed_id bigint NOT NULL,
  borrower_id bigint NOT NULL,
  token text NOT NULL UNIQUE,
  email text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  used_at timestamp with time zone NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT signing_tokens_pkey PRIMARY KEY (id),
  CONSTRAINT signing_tokens_deed_id_fkey FOREIGN KEY (deed_id) REFERENCES public.mortgage_deeds(id) ON DELETE CASCADE,
  CONSTRAINT signing_tokens_borrower_id_fkey FOREIGN KEY (borrower_id) REFERENCES public.borrowers(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_signing_tokens_token ON public.signing_tokens USING btree (token);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_email ON public.signing_tokens USING btree (email);

-- Enable RLS
ALTER TABLE public.signing_tokens ENABLE ROW LEVEL SECURITY;

-- Drop old policy if it exists
DROP POLICY IF EXISTS "Allow public access for signing" ON public.signing_tokens;

-- Create new policies
CREATE POLICY "Allow authenticated users to access signing tokens" ON public.signing_tokens
  FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow public access for reading signing tokens" ON public.signing_tokens
  FOR SELECT USING (true);
```

4. **Click "Run" to execute the SQL**

### Option 2: Using Supabase CLI

If you have the Supabase CLI installed:

1. **Install Supabase CLI** (if not already installed)
   ```bash
   npm install -g supabase
   ```

2. **Login to Supabase**
   ```bash
   supabase login
   ```

3. **Link your project**
   ```bash
   supabase link --project-ref YOUR_PROJECT_REF
   ```

4. **Apply the schema**
   ```bash
   supabase db push
   ```

### Option 3: Using psql (if you have direct database access)

1. **Connect to your database**
   ```bash
   psql -h db.YOUR_PROJECT_REF.supabase.co -U postgres -d postgres
   ```

2. **Run the SQL commands from Option 1**

## Verification

After applying the schema, you can verify it worked by running:

```bash
cd Kolibri-Mortgage-Backend
python3 test_signing_tokens.py
```

You should see:
```
✓ signing_tokens table exists and is accessible
✓ Successfully inserted test signing token
✓ Cleaned up test record
✓ All tests passed!
```

## Troubleshooting

### If you get permission errors:
- Make sure you're using the correct database credentials
- Check that your Supabase project has the necessary permissions

### If the table still doesn't exist:
- Check the SQL execution logs in the Supabase dashboard
- Make sure there are no syntax errors in the SQL commands

### If RLS policies are not working:
- Verify the policies were created correctly
- Check that the user has the correct authentication role

## Next Steps

After creating the table:

1. **Restart your application** to ensure it picks up the changes
2. **Test the mortgage deed creation** to verify signing tokens are created successfully
3. **Check the logs** to confirm no more 404 errors

## Files to Update

- `schema.sql` - Contains the complete database schema
- `test_signing_tokens.py` - Test script to verify table accessibility
- `DATABASE_SETUP.md` - This guide 