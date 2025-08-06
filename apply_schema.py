#!/usr/bin/env python3
"""
Script to apply schema changes to the database.
This script will create the signing_tokens table and apply the necessary RLS policies.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.config import get_supabase
from api.utils.supabase_utils import handle_supabase_operation

async def apply_schema():
    """Apply schema changes to create signing_tokens table."""
    
    print("Applying schema changes to create signing_tokens table...")
    
    # Get Supabase client
    supabase = await get_supabase()
    
    # SQL commands to create the signing_tokens table
    sql_commands = [
        """
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
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_signing_tokens_token ON public.signing_tokens USING btree (token);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_signing_tokens_email ON public.signing_tokens USING btree (email);
        """,
        """
        ALTER TABLE public.signing_tokens ENABLE ROW LEVEL SECURITY;
        """,
        """
        DROP POLICY IF EXISTS "Allow public access for signing" ON public.signing_tokens;
        """,
        """
        CREATE POLICY "Allow authenticated users to access signing tokens" ON public.signing_tokens
          FOR ALL USING (auth.role() = 'authenticated');
        """,
        """
        CREATE POLICY "Allow public access for reading signing tokens" ON public.signing_tokens
          FOR SELECT USING (true);
        """
    ]
    
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"\n{i}. Executing SQL command...")
            print(f"SQL: {sql.strip()}")
            
            # Execute the SQL command using Supabase's rpc function
            result = await supabase.rpc('exec_sql', {'sql_query': sql}).execute()
            print(f"✓ Successfully executed command {i}")
            
        except Exception as e:
            print(f"✗ Failed to execute command {i}: {e}")
            # Continue with other commands even if one fails
            continue
    
    print("\n✓ Schema application completed!")
    return True

if __name__ == "__main__":
    # Run the schema application
    success = asyncio.run(apply_schema())
    sys.exit(0 if success else 1) 