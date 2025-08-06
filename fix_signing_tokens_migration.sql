-- Corrected migration script for signing_tokens table
-- This script handles the existing NOT NULL constraint on borrower_id

-- Step 1: Add new columns
ALTER TABLE public.signing_tokens 
ADD COLUMN IF NOT EXISTS housing_cooperative_signer_id bigint NULL,
ADD COLUMN IF NOT EXISTS signer_type text NOT NULL DEFAULT 'borrower';

-- Step 2: Make borrower_id nullable (required for housing cooperative signers)
ALTER TABLE public.signing_tokens 
ALTER COLUMN borrower_id DROP NOT NULL;

-- Step 3: Add foreign key constraint for housing_cooperative_signer_id
-- First drop the constraint if it exists to avoid errors
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'signing_tokens_housing_cooperative_signer_id_fkey') THEN
        ALTER TABLE public.signing_tokens DROP CONSTRAINT signing_tokens_housing_cooperative_signer_id_fkey;
    END IF;
END $$;

ALTER TABLE public.signing_tokens 
ADD CONSTRAINT signing_tokens_housing_cooperative_signer_id_fkey 
FOREIGN KEY (housing_cooperative_signer_id) REFERENCES public.housing_cooperative_signers(id) ON DELETE CASCADE;

-- Step 4: Add check constraint to ensure proper data integrity
-- First drop the constraint if it exists to avoid errors
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'signing_tokens_signer_check') THEN
        ALTER TABLE public.signing_tokens DROP CONSTRAINT signing_tokens_signer_check;
    END IF;
END $$;

ALTER TABLE public.signing_tokens 
ADD CONSTRAINT signing_tokens_signer_check CHECK (
  (signer_type = 'borrower' AND borrower_id IS NOT NULL AND housing_cooperative_signer_id IS NULL) OR
  (signer_type = 'housing_cooperative_signer' AND housing_cooperative_signer_id IS NOT NULL AND borrower_id IS NULL)
);

-- Step 5: Update existing records to have proper signer_type
UPDATE public.signing_tokens 
SET signer_type = 'borrower' 
WHERE signer_type IS NULL OR signer_type = '';

-- Step 6: Create indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_signing_tokens_housing_cooperative_signer_id ON public.signing_tokens USING btree (housing_cooperative_signer_id);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_signer_type ON public.signing_tokens USING btree (signer_type);

-- Step 7: Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'signing_tokens' 
ORDER BY ordinal_position; 