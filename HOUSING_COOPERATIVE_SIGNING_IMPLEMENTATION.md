# Housing Cooperative Signing Implementation

## Overview

This document describes the implementation of housing cooperative signing functionality in the Mortgage Deed System. The system now supports both borrower signing and housing cooperative signer signing with proper email notifications and database updates.

## Features Implemented

### ✅ 1. Housing Cooperative Email Notifications

**Location**: `api/routers/mortgage_deeds.py` (lines 417-447)

**Functionality**: 
- Sends email notifications to housing cooperative signers when a mortgage deed is created
- Uses the `cooperative_notification.html` template
- Includes deed information and borrower details
- Sends to all housing cooperative signers listed in the deed

**Email Template**: `api/email_templates/cooperative_notification.html`
- Beautiful and fashionable design
- Includes deed reference number, apartment details, and cooperative information
- Lists all borrowers associated with the deed
- Professional styling with clear call-to-action

### ✅ 2. Enhanced Signing Logic

**Location**: `api/routers/signing.py`

**Functionality**:
- Supports both borrower and housing cooperative signer signing
- Automatically detects signer type based on token structure
- Updates appropriate database tables based on signer type
- Updates deed status when all signers have completed signing

**Database Updates**:
- **Borrowers**: Updates `signature_timestamp` in `borrowers` table
- **Housing Cooperative Signers**: Updates `signature_timestamp` in `housing_cooperative_signers` table
- **Deed Status**: Updates `status` in `mortgage_deeds` table

### ✅ 3. Database Schema Updates

**Required Migration**: `update_signing_tokens_schema.sql`

**Changes**:
- Makes `borrower_id` nullable in `signing_tokens` table
- Adds `signer_type` field to distinguish between signer types
- Adds `housing_cooperative_signer_id` field for housing cooperative signers
- Adds proper constraints and indexes
- Maintains backward compatibility

## Signing Flow

### 1. Mortgage Deed Creation
```
1. Create mortgage deed
2. Create borrowers
3. Create housing cooperative signers
4. Send borrower emails with signing links
5. Send housing cooperative signer emails with notifications
```

### 2. Borrower Signing Process
```
1. Borrower clicks email link
2. System validates signing token
3. Updates borrower signature_timestamp
4. Checks if all borrowers have signed
5. Updates deed status to PENDING_HOUSING_COOPERATIVE_SIGNATURE if all borrowers signed
```

### 3. Housing Cooperative Signing Process
```
1. Housing cooperative signer clicks email link
2. System validates signing token
3. Updates housing_cooperative_signers signature_timestamp
4. Checks if all housing cooperative signers have signed
5. Updates deed status to COMPLETED if all signers signed
```

## Database Schema

### Signing Tokens Table
```sql
CREATE TABLE public.signing_tokens (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  deed_id bigint NOT NULL,
  borrower_id bigint NULL,  -- Nullable for housing cooperative signers
  housing_cooperative_signer_id bigint NULL,  -- New field
  signer_type text NOT NULL DEFAULT 'borrower',  -- New field
  token text NOT NULL UNIQUE,
  email text NOT NULL,
  expires_at timestamp with time zone NOT NULL,
  used_at timestamp with time zone NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT signing_tokens_signer_check CHECK (
    (signer_type = 'borrower' AND borrower_id IS NOT NULL AND housing_cooperative_signer_id IS NULL) OR
    (signer_type = 'housing_cooperative_signer' AND housing_cooperative_signer_id IS NOT NULL AND borrower_id IS NULL)
  )
);
```

## API Endpoints

### Signing Endpoint
- **URL**: `POST /api/signing/sign`
- **Functionality**: Handles both borrower and housing cooperative signer signing
- **Request Body**: `{"token": "signing_token"}`
- **Response**: Updated signing status and deed information

### Email Templates
- **Borrower**: `borrower_notification.html` - Beautiful signing page with call-to-action
- **Housing Cooperative**: `cooperative_notification.html` - Professional notification with deed details

## Status Flow

```
CREATED → PENDING_BORROWER_SIGNATURE → PENDING_HOUSING_COOPERATIVE_SIGNATURE → COMPLETED
```

1. **CREATED**: Initial state when deed is created
2. **PENDING_BORROWER_SIGNATURE**: When all borrowers have signed
3. **PENDING_HOUSING_COOPERATIVE_SIGNATURE**: When all housing cooperative signers have signed
4. **COMPLETED**: Final state when all parties have signed

## Testing

### Test Scripts
- `test_housing_cooperative_signing.py`: Basic functionality test
- `test_complete_signing_flow.py`: Comprehensive flow test

### Manual Testing
1. Create a mortgage deed with borrowers and housing cooperative signers
2. Verify emails are sent to all parties
3. Test signing flow for both borrower and housing cooperative signer
4. Verify database updates and status changes

## Implementation Notes

### Email Logic
- Borrower emails are sent during deed creation with signing links
- Housing cooperative emails are sent during deed creation with notifications
- Both use appropriate templates with professional styling

### Database Updates
- `signature_timestamp` is updated in the appropriate table based on signer type
- Deed status is updated automatically when all signers of a type have signed
- All updates are wrapped in proper error handling

### Security
- Signing tokens are unique and time-limited
- Tokens are marked as used after signing
- Proper validation ensures only authorized signers can sign

## Next Steps

1. **Apply Database Migration**: Run `update_signing_tokens_schema.sql` in Supabase
2. **Test Email Delivery**: Verify emails are being sent correctly
3. **Test Signing Flow**: Verify both borrower and housing cooperative signing works
4. **Monitor Logs**: Check for any errors in the signing process

## Files Modified

1. `api/routers/mortgage_deeds.py` - Added housing cooperative email logic
2. `api/routers/signing.py` - Enhanced signing logic for both signer types
3. `api/email_templates/cooperative_notification.html` - Housing cooperative email template
4. `update_signing_tokens_schema.sql` - Database migration script
5. `test_housing_cooperative_signing.py` - Test script
6. `test_complete_signing_flow.py` - Comprehensive test script 