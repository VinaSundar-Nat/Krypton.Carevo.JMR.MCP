# Krypton.Carevo.JMR.MCP

An MCP (Model Context Protocol) server implementation for job listing and management services with MongoDB integration and streamable HTTP service.

## Project Overview

This project implements a modern MCP server with comprehensive tooling for job listing management, database operations, and real-time job analytics. It provides:

- **Job Listing Management**: Create, retrieve, and filter job listings
- **Job View Tracking**: Track and analyze job listing views
- **MCP Resources**: URI-based read-only access to job listings and view data
- **MCP Tools**: Standardized tool definitions for AI model integration
- **MongoDB Integration**: Async database operations using Beanie ODM
- **REST API**: Starlette-based HTTP transport layer

## Architecture

### Project Structure

```
Krypton.Carevo.JMR.MCP/
├── libraries/
│   └── jmr-lib/
│       ├── src/
│       │   ├── components/
│       │   │   ├── resources/
│       │   │   │   └── job_listing.py     # Job listing resources
│       │   │   └── tools/
│       │   │       ├── job_listing.py      # Job listing tools
│       │   │       └── schemas/            # JSON schema definitions
│       │   ├── models/
│       │   │   ├── domain/jobs/           # Job domain models
│       │   │   ├── context/               # Database context
│       │   │   └── handler/               # Tool & resource handler base
│       │   └── utility/                    # Logging and config
│       ├── pyproject.toml
│       └── requirements.txt
├── servers/
│   └── jmr-svc/
│       ├── src/
│       │   ├── main.py                     # FastMCP server entry
│       │   ├── config.py                   # Configuration management
│       │   ├── managers/                   # MongoDB context manager
│       │   ├── services/                   # MCP services
│       │   └── helpers/                    # Tool registration
│       ├── pyproject.toml
│       └── requirements.txt
├── docs/                                    # Documentation images
├── .vscode/                                 # VSCode configuration
└── README.md
```

## Key Features

### 1. MCP Resources

Resources provide direct access to job listing data through URI-based endpoints. These are read-only endpoints that expose job data in JSON format.

#### jobs://today
Access only active job listings (non-closed positions posted today).

**URI:** `jobs://today`  
**MIME Type:** `application/json`  
**Description:** Returns all active job listings that were posted on or after the current date.

**Response:** Array of Job objects (views array excluded for privacy)

#### jobs://details/{job_id}
Access detailed information for a specific job listing by ID.

**URI:** `jobs://details/{job_id}`  
**MIME Type:** `application/json`  
**Description:** Fetches comprehensive details for a single job listing, including view count.

**Parameters:**
- `job_id`: The unique identifier for the job listing

**Response:** Single Job object with `view_count` field (views array excluded for privacy)

#### jobs://views/{job_id}
Get view count for a specific job listing by ID.

**URI:** `jobs://views/{job_id}`  
**MIME Type:** `application/json`  
**Description:** Retrieves the total number of views for a specific job listing.

**Parameters:**
- `job_id`: The unique identifier for the job listing

**Response:**
```json
{
  "job_id": "job_123456",
  "view_count": 5
}
```

### 2. MCP Tools

#### fetch_job_listings
Fetch job listings with advanced filtering capabilities.

**Input Schema:**
- `filter`: JobFilter object with optional criteria:
  - `job_id`: Filter by job ID
  - `company`: Filter by company name
  - `location`: Filter by job location
  - `job_type`: Full Time, Part Time, Contract, Intern, Temporary
  - `connection_type`: Onsite, Remote, Hybrid
  - `skills`: Array of required skills
  - `posted_from` / `posted_to`: Date range filtering
  - `operator`: AND or OR logic for filter conditions

**Response:** List of Job objects (views array excluded for privacy)

#### create_job_listing
Create a new job listing in the database.

**Input Schema:**
- `job`: Complete Job object with all required fields

**Response:** Created Job object with ID

#### create_job_view
Track user views on job listings.

**Input Schema:**
- `job_id`: ID of the job listing
- `user_id`: ID of the user viewing the job

**Response:** View metadata with action (created/updated) and total_job_views count

#### get_job_views
Retrieve view count and metadata for a job.

**Input Schema:**
- `jobid`: Job ID

**Response:** List of View records for the job

### 2. Data Models

#### Job
```python
job_id: str (unique)
title: str
description: str
company: str
location: str
job_type: JobType (enum)
connection_type: ConnectionType (enum)
salary_range: Dict[str, Any]
posted_date: str
skills: List[str]
views: List[View] (not exposed in API)
source: str
created_at: str
updated_at: str
view_count: int (computed field)
```

#### JobFilter
Filtering criteria for job queries with AND/OR operators.

#### View
```python
user_id: str
view_date: str
```

## Testing

### MongoDB Testing with mongosh

Use mongosh to verify data persistence and structure:

![MongoDB shell interaction](docs/mongosh.png)

#### mongosh Setup and Usage

**1. Connect to MongoDB:**
```bash
mongosh "mongodb://username:password@host:port/database"
```

**2. Verify Job Collections:**
```javascript
// List all jobs
db.job.find().pretty()

// Find specific job
db.job.findOne({ job_id: "job_123456" })

// Search by company
db.job.find({ company: "Tech Innovations Inc" }).pretty()

// Check views on a job
db.job.findOne({ job_id: "job_123456" }).views

// Count total jobs
db.job.countDocuments()

// Find jobs with specific skills
db.job.find({ skills: { $in: ["Python", "FastAPI"] } }).pretty()

// Filter by location and job type
db.job.find({ 
  location: "Remote", 
  job_type: "Full Time" 
}).pretty()
```

**3. Verify View Data:**
```javascript
// Check if views are being saved
db.job.findOne({ job_id: "job_123456" }, { views: 1 })

// Count views for a specific job
db.job.aggregate([
  { $match: { job_id: "job_123456" } },
  { $project: { view_count: { $size: "$views" } } }
])

// Find jobs sorted by view count
db.job.aggregate([
  { $addFields: { view_count: { $size: "$views" } } },
  { $sort: { view_count: -1 } },
  { $limit: 10 }
])
```

**4. Data Management:**
```javascript
// Delete a job listing
db.job.deleteOne({ job_id: "job_123456" })

// Update job details
db.job.updateOne(
  { job_id: "job_123456" },
  { $set: { title: "New Title", updated_at: new Date().toISOString() } }
)

// Clear all views for a job (reset view tracking)
db.job.updateOne(
  { job_id: "job_123456" },
  { $set: { views: [] } }
)
```

### MCP Client Testing with Postman

Test MCP tools and resources using the Postman client:

![Postman MCP client](docs/client_pm.png)

#### Postman Setup for MCP Testing

**1. Create a New Request:**
- Method: `POST`
- URL: `http://127.0.0.1:8445/job-listing/sse` (or appropriate endpoint)

**2. Set Headers:**
```
Content-Type: application/json
Accept: application/json
```

**3. Resource Test Cases:**

#### Test Case R1: Access Today's Active Jobs
```json
{
  "method": "resources/read",
  "params": {
    "uri": "jobs://today"
  }
}
```

**Expected Response:** Array of active job listings posted today (views excluded)

#### Test Case R2: Get Job Details by ID
```json
{
  "method": "resources/read",
  "params": {
    "uri": "jobs://details/job_123456"
  }
}
```

**Expected Response:** Single job object with view_count field

#### Test Case R3: Get Job View Count
```json
{
  "method": "resources/read",
  "params": {
    "uri": "jobs://views/job_123456"
  }
}
```

**Expected Response:**
```json
{
  "job_id": "job_123456",
  "view_count": 5
}
```

**4. Tool Test Cases:**

#### Test Case 1: Fetch All Job Listings
```json
{
  "method": "tools/call",
  "params": {
    "name": "fetch_job_listings",
    "arguments": {
      "filter": {}
    }
  }
}
```

#### Test Case 2: Fetch with Filters
```json
{
  "method": "tools/call",
  "params": {
    "name": "fetch_job_listings",
    "arguments": {
      "filter": {
        "company": "Tech Innovations Inc",
        "location": "Remote",
        "job_type": "Full Time",
        "skills": ["Python", "FastAPI"],
        "operator": "AND"
      }
    }
  }
}
```

#### Test Case 3: Create a New Job Listing
```json
{
  "method": "tools/call",
  "params": {
    "name": "create_job_listing",
    "arguments": {
      "job": {
        "job_id": "job_123456",
        "title": "Senior Full Stack Developer",
        "description": "We are seeking an experienced Full Stack Developer...",
        "company": "Tech Innovations Inc",
        "location": "San Francisco, CA",
        "job_type": "Full Time",
        "connection_type": "Hybrid",
        "salary_range": {
          "min": 120000,
          "max": 180000,
          "currency": "USD"
        },
        "posted_date": "2026-01-15T10:00:00Z",
        "skills": ["Python", "FastAPI", "React", "MongoDB"],
        "source": "company_website",
        "created_at": "2026-01-15T10:00:00Z",
        "updated_at": "2026-01-15T10:00:00Z"
      }
    }
  }
}
```

#### Test Case 4: Create or Update a Job View
```json
{
  "method": "tools/call",
  "params": {
    "name": "create_job_view",
    "arguments": {
      "job_id": "job_123456",
      "user_id": "user_789"
    }
  }
}
```

#### Test Case 5: Get Job Views and Count
```json
{
  "method": "tools/call",
  "params": {
    "name": "get_job_views",
    "arguments": {
      "jobid": "job_123456"
    }
  }
}
```

#### Postman Testing Workflow

**Step 1: Create a Job**
- Use Test Case 3 to create a job listing
- Verify response includes the created job with ID

**Step 2: Verify in MongoDB**
- Open mongosh and run: `db.job.findOne({ job_id: "job_123456" })`
- Confirm all fields are saved correctly
- Check that views array is empty: `[]`

**Step 3: Create Multiple Views**
- Run Test Case 4 multiple times with different user_ids
- Example: `user_789`, `user_790`, `user_791`
- Each call creates or updates a view for that user

**Step 4: Verify Views in MongoDB**
```javascript
db.job.findOne({ job_id: "job_123456" }, { views: 1, view_count: 1 })
```
- Should show array of View objects with user_ids and view_dates
- `view_count` should equal the number of views

**Step 5: Fetch Job and Confirm Privacy**
- Run Test Case 1 to fetch the job
- **Important**: Response should NOT include the `views` array
- Response should only show `view_count` (computed field)
- This ensures user privacy - no one can see who viewed the job

**Step 6: Filter Jobs by Criteria**
- Run Test Case 2 with various filter combinations
- Test each filter parameter independently
- Test AND/OR operators with multiple conditions

#### Postman Response Validation

**Expected fetch_job_listings Response:**
```json
[
  {
    "job_id": "job_123456",
    "title": "Senior Full Stack Developer",
    "company": "Tech Innovations Inc",
    "location": "San Francisco, CA",
    "job_type": "Full Time",
    "connection_type": "Hybrid",
    "salary_range": { "min": 120000, "max": 180000, "currency": "USD" },
    "posted_date": "2026-01-15T10:00:00Z",
    "skills": ["Python", "FastAPI", "React", "MongoDB"],
    "source": "company_website",
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z",
    "view_count": 3
  }
]
```
**Note**: No `views` array in response (privacy protection)

**Expected create_job_view Response:**
```json
{
  "job_id": "job_123456",
  "user_id": "user_789",
  "view_date": "2026-01-16T14:30:00.123456+00:00",
  "action": "created",
  "total_job_views": 1
}
```

**Example fetch_job_listings request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fetch_job_listings",
    "arguments": {
      "filter": {
        "company": "Tech Innovations Inc",
        "location": "Remote",
        "job_type": "Full Time",
        "skills": ["Python", "FastAPI"]
      }
    }
  }
}
```

**Example create_job_view request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "create_job_view",
    "arguments": {
      "job_id": "job_123456",
      "user_id": "user_789"
    }
  }
}
```

## Configuration

### Environment Variables

Located in `config.py`:
- `MONGO_URI`: MongoDB connection URI
- `MONGO_USERNAME`: MongoDB username
- `MONGO_PASSWORD`: MongoDB password
- `MONGO_DB`: Database name
- `API_ENDPOINT`: API host and port
- `ORIGINS`: CORS allowed origins

### Dependencies

**Core:**
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `pydantic`: Data validation
- `pymongo`: MongoDB driver
- `beanie`: MongoDB ODM
- `python-mcp`: Model Context Protocol

**Development:**
- `debugpy`: Python debugger
- `pytest`: Testing framework

## Development

### Installation

```bash
# Install project dependencies
./install.sh

# Or manually:
cd libraries/jmr-lib && pip install -e .
cd ../../servers/jmr-svc && pip install -e .
```

### Running the Server

```bash
# Start development server
python servers/jmr-svc/src/main.py

# With debugging
# Use VSCode launch configuration: Debug JMR Service
```

### Database Initialization

MongoDB client is initialized in `app_lifespan()` context manager:
- Automatic connection with connection pooling
- Beanie ODM initialization
- Connection health check with ping

### Tool Registration

Tools are registered via `ToolRegister` helper:
1. Handler implements `BaseToolHandler`
2. Defines tool schemas in `@property tools`
3. Schema loader converts JSON schema to Python type annotations
4. FastMCP registers tools with proper signatures

### Resource Registration

Resources are registered via `ResourceRegister` helper:
1. Handler implements `BaseResourceHandler`
2. Defines resources in `@property resources` with URI patterns
3. Implements `read_resource(uri)` method for handling URI-based reads
4. FastMCP registers resources with proper URI routing

## Privacy & Security

- **View Privacy**: User view data is stored in database but excluded from API responses
- **View Count**: Publicly visible via `view_count` computed field
- **Database Exclusion**: Views marked with `Field(default=[])` for storage, excluded in responses with `model_dump(exclude={'views'})`

## Recent Updates

### MCP Resources Implementation
- Added three URI-based resources for read-only job access:
  - `jobs://today`: Active job listings posted today
  - `jobs://details/{job_id}`: Detailed job information by ID
  - `jobs://views/{job_id}`: View count for specific job
- Resources provide JSON-formatted data with privacy protection (views excluded)
- Implemented `BaseResourceHandler` for resource handling architecture
- Resource registration system integrated with FastMCP

### Schema Externalization
- Job filter schema: `components/tools/schemas/job_filter_schema.json`
- Job creation schema: `components/tools/schemas/job_schema.json`
- Job view schema: `components/tools/schemas/job_view_schema.json`

### View Handling
- Views now properly persisted to MongoDB
- Privacy protection: views excluded from fetch/create responses
- View count available through computed property

### Type System
- Enhanced tool registration with proper Python type annotations
- Schema-to-type conversion for MCP client compatibility
- Full enum support for job_type and connection_type

## Debugging

### Breakpoint Issues
If breakpoints aren't hitting:
1. Verify `.vscode/launch.json` configuration
2. Ensure `justMyCode: false` is set
3. Check PYTHONPATH includes both library and service directories
4. Restart the Python interpreter

## License

Internal tool - Krypton.Carevo.JMR.MCP
