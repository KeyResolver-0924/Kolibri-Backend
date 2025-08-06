-- Create signing_tokens table
CREATE TABLE IF NOT EXISTS public.signing_tokens (
    id SERIAL PRIMARY KEY,
    deed_id INTEGER NOT NULL REFERENCES public.mortgage_deeds(id) ON DELETE CASCADE,
    borrower_id INTEGER NOT NULL REFERENCES public.borrowers(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_signing_tokens_token ON public.signing_tokens(token);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_deed_id ON public.signing_tokens(deed_id);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_borrower_id ON public.signing_tokens(borrower_id);
CREATE INDEX IF NOT EXISTS idx_signing_tokens_email ON public.signing_tokens(email);

-- Enable Row Level Security
ALTER TABLE public.signing_tokens ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Allow authenticated users to access signing tokens" ON public.signing_tokens
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow public access for reading signing tokens" ON public.signing_tokens
    FOR SELECT USING (true); 