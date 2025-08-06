# Fix for Signing Tokens Issues

## Problem Summary
1. **Database Schema Mismatch**: The `signing_tokens` table doesn't have the required fields for housing cooperative signers
2. **Syntax Error**: Missing `await` keyword in mortgage_deeds.py
3. **Sign Buttons Not Working**: Tokens not being saved to database

## Root Causes
1. The current `signing_tokens` table only has `borrower_id` field, but the code tries to insert `housing_cooperative_signer_id` and `signer_type`
2. There was a syntax error in the try-except block in mortgage_deeds.py
3. The database schema needs to be updated to support both borrower and housing cooperative signer tokens

## Solutions

### 1. Database Schema Update

Run the following SQL in your Supabase SQL Editor:

```sql
-- Migration script to update signing_tokens table for housing cooperative signers

-- Add new columns to existing signing_tokens table
ALTER TABLE public.signing_tokens 
ADD COLUMN IF NOT EXISTS housing_cooperative_signer_id bigint NULL,
ADD COLUMN IF NOT EXISTS signer_type text NOT NULL DEFAULT 'borrower';

-- Add foreign key constraint for housing_cooperative_signer_id
ALTER TABLE public.signing_tokens 
ADD CONSTRAINT IF NOT EXISTS signing_tokens_housing_cooperative_signer_id_fkey 
FOREIGN KEY (housing_cooperative_signer_id) REFERENCES public.housing_cooperative_signers(id) ON DELETE CASCADE;

-- Add check constraint to ensure proper data integrity
ALTER TABLE public.signing_tokens 
DROP CONSTRAINT IF EXISTS signing_tokens_signer_check;

ALTER TABLE public.signing_tokens 
ADD CONSTRAINT signing_tokens_signer_check CHECK (
  (signer_type = 'borrower' AND borrower_id IS NOT NULL AND housing_cooperative_signer_id IS NULL) OR
  (signer_type = 'housing_cooperative_signer' AND housing_cooperative_signer_id IS NOT NULL AND borrower_id IS NULL)
);

-- Update existing records to have proper signer_type
UPDATE public.signing_tokens 
SET signer_type = 'borrower' 
WHERE signer_type IS NULL OR signer_type = '';

-- Create index for the new column
CREATE INDEX IF NOT EXISTS idx_signing_tokens_housing_cooperative_signer_id ON public.signing_tokens USING btree (housing_cooperative_signer_id);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_signer_type ON public.signing_tokens USING btree (signer_type);
```

### 2. Code Fixes

The syntax error in `api/routers/mortgage_deeds.py` has been fixed. The code now properly handles:
- Borrower signing tokens with `signer_type: "borrower"`
- Housing cooperative signer tokens with `signer_type: "housing_cooperative_signer"`

### 3. Updated Schema

The `schema.sql` file has been updated to include the new fields:
- `housing_cooperative_signer_id` (nullable)
- `signer_type` (text, defaults to 'borrower')
- Proper foreign key constraints
- Check constraint to ensure data integrity

## Testing the Fix

### 1. Test Database Schema
```bash
cd Kolibri-Mortgage-Backend
python test_database_schema.py
```

### 2. Test Signing Token Creation
```bash
python test_signing_tokens.py
```

### 3. Test Complete Flow
```bash
python test_complete_housing_cooperative_signing.py
```

## Verification Steps

1. **Check Database Schema**:
   ```sql
   -- Run in Supabase SQL Editor
   SELECT column_name, data_type, is_nullable 
   FROM information_schema.columns 
   WHERE table_name = 'signing_tokens';
   ```

2. **Check Existing Tokens**:
   ```sql
   -- Run in Supabase SQL Editor
   SELECT id, deed_id, borrower_id, housing_cooperative_signer_id, signer_type, email 
   FROM signing_tokens 
   LIMIT 10;
   ```

3. **Test Token Creation**:
   - Create a new mortgage deed
   - Check if signing tokens are created in the database
   - Verify emails are sent with working signing links

## Expected Behavior After Fix

1. **Token Creation**: Signing tokens will be properly saved to the database
2. **Email Links**: Signing links in emails will work correctly
3. **Signing Process**: Both borrowers and housing cooperative signers can sign successfully
4. **Status Updates**: Deed status will update correctly as people sign

## Troubleshooting

### If tokens still aren't being created:
1. Check the application logs for errors
2. Verify the database schema has been updated
3. Ensure the RLS policies allow token creation

### If signing links don't work:
1. Check if the tokens exist in the database
2. Verify the signing endpoint is accessible
3. Check browser console for JavaScript errors

### If emails aren't being sent:
1. Check Mailgun configuration
2. Verify email templates exist
3. Check application logs for email errors

## Files Modified

1. `schema.sql` - Updated table structure
2. `api/routers/mortgage_deeds.py` - Fixed syntax error
3. `update_signing_tokens_schema.sql` - Migration script
4. `FIX_SIGNING_TOKENS.md` - This documentation

## Next Steps

1. Apply the database migration
2. Restart the application
3. Test creating a new mortgage deed
4. Verify signing tokens are created
5. Test the signing process end-to-end 