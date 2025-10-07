# Fix Scheduler Service 500 Error

## Root Cause
The scheduler service database tables don't exist. The service is running but can't query the database.

## Solution: Create Database Schema

### Option 1: Via Docker (When Server Accessible)

```bash
# SSH to server
ssh -i "path/to/server.pem" omar@192.168.75.20

# Copy the schema file to container
docker cp ~/git/scheduler-service/schema.sql omarino-postgres:/tmp/schema.sql

# Execute the schema
docker exec -it omarino-postgres psql -U omarino_user -d omarino_ems -f /tmp/schema.sql

# Restart scheduler service to ensure clean state
sudo docker restart omarino-scheduler

# Check logs
sudo docker logs omarino-scheduler --tail 50
```

### Option 2: Via psql Directly

```bash
# Connect to PostgreSQL
docker exec -it omarino-postgres psql -U omarino_user -d omarino_ems

# Then paste the contents of scheduler-service/schema.sql
```

### Option 3: Via PgAdmin/DBeaver
1. Connect to database: `192.168.75.20:5432`
2. Database: `omarino_ems`
3. User: `omarino_user`
4. Open SQL editor
5. Paste contents of `scheduler-service/schema.sql`
6. Execute

## Verification

After creating the tables, test in browser console:

```javascript
// Should now return empty array instead of 500
fetch('https://ems-back.omarino.net/api/scheduler/workflows')
  .then(r => r.json())
  .then(data => console.log('Workflows:', data));
```

## What the Schema Creates

1. **WorkflowDefinitions** - Stores workflow configurations
2. **WorkflowExecutions** - Tracks workflow run history  
3. **TaskExecutions** - Tracks individual task executions
4. **__EFMigrationsHistory** - EF Core migration tracking

After this, workflow creation should work! 🚀
