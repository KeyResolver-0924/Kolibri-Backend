### Product Requirements Document (PRD): Mortgage Deed Management API Backend

#### Purpose

This PRD outlines the development of a REST API backend for a digital mortgage deed management system. The backend will be implemented using Python with FastAPI and Supabase for the database. The document is targeted at developers and includes feature definitions, implementation order, and necessary details to deliver the backend efficiently.

---

### Tech Stack

- **Backend Framework:** Python with FastAPI
- **Database:** Supabase (PostgreSQL)
- **Authentication:** Supabase Auth (JWT-based)
- **Email Notifications:** Integration with Mailgun for email notifications
- **Database Interactions:** Supabase Python SDK for all database interactions

---

### Features

#### 1. Mortgage Deed CRUD Operations

##### **Endpoints:**

1. **Create a Mortgage Deed**

   - Input:
     - Date of creation
     - Credit number
     - BRF organization number
     - Housing cooperative name
     - Housing cooperative address
     - Apartment address
     - Apartment number
     - Borrower details (name, personal number, email, ownership percentage)
     - Economic administrator details (name, personal number, email)
   - Response: Created deed object with unique ID.

2. **Read Mortgage Deed Details**

   - Input: Deed ID
   - Response: Full details of the deed.

3. **Update Mortgage Deed**

   - Input: Deed ID + fields to update.
   - Response: Updated deed object.

4. **Delete Mortgage Deed**

   - Input: Deed ID
   - Response: Confirmation of deletion.

---

#### 2. Fetch Housing Cooperative Details

##### **Endpoints:**

1. **Get Housing Cooperative Details**

   - Input: BRF organization number
   - Response:
     - Housing cooperative name
     - Address (street, postal code, city)
     - Economic administrator details (name, personal number, email)

---

#### 3. Send Deed for Signing

##### **Flow:**

1. **Trigger Signing Process:** Endpoint to initiate the signing process for a specific deed.
2. **Notify Parties:**
   - Use some minimalistic templating system for email
   - Send email to the borrower(s).
   - Send email to the housing cooperative.
   - (Optional) Notify the bank (future extension).
3. **Update Status:**
   - Status transitions:
     - `CREATED` ➔ `PENDING_BORROWER_SIGNATURE`
     - `PENDING_BORROWER_SIGNATURE` ➔ `PENDING_HOUSING_COOPERATIVE_SIGNATURE`
     - `PENDING_HOUSING_COOPERATIVE_SIGNATURE` ➔ `COMPLETED`
4. **Log Time Stamps:**
   - Track time spent in each status for statistical analysis.
5. **Audit Log:**
   - Maintain an audit log for all actions in the signing process, including:
     - Action type (e.g., status update, email sent, signature completed).
     - Timestamp.
     - User/party initiating the action.

##### **Endpoints:**

- `POST /deeds/{id}/send-for-signing`

  - Input: Deed ID
  - Response: Confirmation of initiation and updated status.

- `GET /deeds/{id}/audit-log`
  - Input: Deed ID
  - Response: List of all audit log entries for the deed.

---

#### 4. List and Filter Mortgage Deeds

##### **Filters:**

- By apartment owner (name or personal number)
- By housing cooperative (organization number or name)
- By deed status (e.g., `CREATED`, `COMPLETED`)
- By creation date range
- By person number (to retrieve deeds awaiting signature by a specific party)

##### **Endpoints:**

- `GET /deeds`

  - Input: Filter parameters (optional)
  - Response: List of deeds matching the filters.

- `GET /deeds/pending-signature/{person_number}`

  - Input: Person number
  - Response: List of deeds awaiting signature by the given person.

---

#### 5. Statistics and Analytics

##### **Metrics:**

1. Total number of deeds.
2. Count of deeds in each status.
3. Average time spent in each status.

##### **Endpoints:**

- `GET /stats/summary`

  - Response: JSON object with aggregated statistics.

- `GET /stats/status-duration`

  - Response: JSON object with average duration per status.

---

#### SQL Schema

- SQL Schema for the database is provided in the `schema.sql` file.

### Implementation Plan

#### Phase 1: Core CRUD Functionality

- Set up the FastAPI project and Supabase integration.
- Implement basic CRUD operations for mortgage deeds using Supabase Python SDK.
- Write unit tests for CRUD endpoints.

#### Phase 2: Fetch Cooperative Details

- Develop an endpoint to fetch housing cooperative details using Supabase Python SDK.
- Write unit tests for cooperative details endpoint.

#### Phase 3: Signing Workflow

- Develop endpoints for initiating the signing process.
- Integrate email notification service using Mailgun.
- Implement status transitions and time-stamp logging.
- Implement an audit log for the end-to-end signing process.
- Write unit and integration tests for the signing workflow.

#### Phase 4: Filtering and Listing

- Implement filtering logic in the database queries using Supabase Python SDK.
- Build endpoints to retrieve filtered results.
- Optimize query performance for large datasets.
- Write unit tests for filtering and listing.

#### Phase 5: Statistics and Analytics

- Create SQL queries or Supabase views for aggregating statistics using Supabase Python SDK.
- Build endpoints to serve statistical data.
- Write unit tests for analytics endpoints.

#### Phase 6: Documentation

- Write API documentation using tools like Redoc.

---

### API Authentication and Authorization

- Use Supabase Auth to secure endpoints.
- Assign roles for access control:
  - **Admin:** Full access to all endpoints.
  - **Borrower:** Identified by personal number, access to deeds related to them.
  - **Housing Cooperative Representative:** Identified by personal number, access to deeds related to their cooperative.
  - **Bank Clerk:** This is the supebase authed user, belongs to a bank. A bank has many clerks.

---

### Additional Considerations

1. **Error Handling:**

   - Standardize error responses with appropriate HTTP status codes.
   - Include detailed error messages for debugging.

2. **Data Validation:**

   - Use Pydantic models to validate input data.

3. **Scalability:**

   - Design database schema and queries to handle high volumes of deeds and concurrent requests.

4. **Logging:**

   - Log all API requests and responses for debugging and auditing.
   - Maintain an audit log for critical actions and events in the system.

5. **Future Extensions:**

   - Integration with external systems for automatic status updates (e.g., bank systems).
   - Multi-language support for email notifications and UI.

---

### Docs

#### Supabase Async example

```
from supabase._async.client import AsyncClient as Client, create_client

async def create_supabase() -> Client:
    return await create_client(url, key)
```
