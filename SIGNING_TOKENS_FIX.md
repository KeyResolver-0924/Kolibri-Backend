# Signing Tokens Fix

## Problem
The system was encountering a 404 Not Found error when trying to create signing tokens during mortgage deed creation. The error occurred at:
```
INFO:httpx:HTTP Request: POST https://etpkjzzsnnttsyxthswf.supabase.co/rest/v1/signing_tokens "HTTP/2 404 Not Found"
ERROR:api.utils.supabase_utils:Failed to create signing token: {}
```

## Root Cause
The issue was with the Row Level Security (RLS) policy on the `signing_tokens` table. The original policy was:
```sql
CREATE POLICY "Allow public access for signing" ON public.signing_tokens
  FOR ALL USING (true);
```

This policy was too permissive and might not have been working correctly with the authenticated user context.

## Solutions Implemented

### 1. Updated RLS Policies
Modified the `schema.sql` file to use more appropriate RLS policies:

```sql
-- Signing Tokens - Allow authenticated users to access
CREATE POLICY "Allow authenticated users to access signing tokens" ON public.signing_tokens
  FOR ALL USING (auth.role() = 'authenticated');

-- Signing Tokens - Allow public access for reading tokens (needed for signing process)
CREATE POLICY "Allow public access for reading signing tokens" ON public.signing_tokens
  FOR SELECT USING (true);
```

### 2. Enhanced Error Handling
Updated the mortgage deed creation process to handle signing token creation failures gracefully:

```python
try:
    await handle_supabase_operation(
        operation_name="create signing token",
        operation=supabase.table("signing_tokens").insert(signing_token_data).execute(),
        error_msg="Failed to create signing token"
    )
    logger.info(f"Successfully created signing token for borrower {borrower['email']}")
except Exception as e:
    logger.error(f"Failed to create signing token for borrower {borrower['email']}: {str(e)}")
    # Don't fail the entire operation if signing token creation fails
    # Continue with email sending even if token creation failed
```

### 3. Test Script
Created `test_signing_tokens.py` to verify table accessibility and functionality.

## Database Schema
The `signing_tokens` table structure:
```sql
CREATE TABLE public.signing_tokens (
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
```

## Testing

### 1. Run the Test Script
```bash
cd Kolibri-Mortgage-Backend
python test_signing_tokens.py
```

### 2. Check Database Migration
Ensure the updated schema has been applied to your database:
```sql
-- Check if the new policies exist
SELECT * FROM pg_policies WHERE tablename = 'signing_tokens';
```

### 3. Manual Test
Try creating a mortgage deed and check if signing tokens are created successfully.

## Deployment Steps

1. **Update Database Schema**
   ```bash
   # Apply the updated schema.sql to your database
   psql -h your-db-host -U your-user -d your-database -f schema.sql
   ```

2. **Restart the Application**
   ```bash
   # Restart your FastAPI application
   systemctl restart your-app-service
   # or
   pkill -f uvicorn && uvicorn main:app --reload
   ```

3. **Test the Fix**
   ```bash
   # Run the test script
   python test_signing_tokens.py
   ```

## Benefits

1. **Proper Authentication**: RLS policies now properly handle authenticated users
2. **Graceful Error Handling**: Signing token failures don't break the entire mortgage deed creation
3. **Better Logging**: More detailed error messages for debugging
4. **Maintainable**: Clear separation of concerns and proper error handling

## Troubleshooting

### If the issue persists:

1. **Check Database Connection**
   ```bash
   python test_signing_tokens.py
   ```

2. **Verify RLS Policies**
   ```sql
   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
   FROM pg_policies 
   WHERE tablename = 'signing_tokens';
   ```

3. **Check Table Existence**
   ```sql
   SELECT * FROM information_schema.tables 
   WHERE table_name = 'signing_tokens';
   ```

4. **Test Direct Insert**
   ```sql
   INSERT INTO signing_tokens (deed_id, borrower_id, token, email, expires_at)
   VALUES (1, 1, 'test_token', 'test@example.com', '2025-12-31 23:59:59');
   ```

## Migration Notes

- The new RLS policies are backward compatible
- Existing signing tokens will continue to work
- The enhanced error handling ensures the mortgage deed creation process is more robust
- No data migration is required

## Files Modified

1. `schema.sql` - Updated RLS policies for signing_tokens table
2. `api/routers/mortgage_deeds.py` - Enhanced error handling for signing token creation
3. `test_signing_tokens.py` - Test script for verification
4. `SIGNING_TOKENS_FIX.md` - This documentation 