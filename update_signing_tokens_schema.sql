-- Migration script to update signing_tokens table for housing cooperative signers
-- Run this script in your Supabase SQL editor

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