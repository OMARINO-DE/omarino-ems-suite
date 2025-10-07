-- Scheduler Service Database Schema
-- Run this script to create the required tables for the scheduler service

-- Create WorkflowDefinitions table
CREATE TABLE IF NOT EXISTS "WorkflowDefinitions" (
    "Id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "Name" varchar(200) NOT NULL,
    "Description" text,
    "IsEnabled" boolean NOT NULL DEFAULT true,
    "Tasks" jsonb NOT NULL,
    "Schedule" jsonb,
    "Tags" jsonb,
    "MaxExecutionTime" interval NOT NULL DEFAULT '01:00:00',
    "MaxRetries" int NOT NULL DEFAULT 3,
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT now(),
    "UpdatedAt" timestamp with time zone NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS "IX_WorkflowDefinitions_Name" ON "WorkflowDefinitions" ("Name");

-- Create WorkflowExecutions table
CREATE TABLE IF NOT EXISTS "WorkflowExecutions" (
    "Id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "WorkflowId" uuid NOT NULL,
    "Status" int NOT NULL DEFAULT 0,  -- 0=Pending, 1=Running, 2=Completed, 3=Failed, 4=Cancelled
    "TriggerType" int NOT NULL DEFAULT 0,  -- 0=Manual, 1=Scheduled, 2=Webhook
    "CreatedAt" timestamp with time zone NOT NULL DEFAULT now(),
    "StartedAt" timestamp with time zone,
    "CompletedAt" timestamp with time zone,
    "Error" text,
    "Output" jsonb,
    CONSTRAINT "FK_WorkflowExecutions_WorkflowDefinitions" 
        FOREIGN KEY ("WorkflowId") 
        REFERENCES "WorkflowDefinitions" ("Id") 
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "IX_WorkflowExecutions_WorkflowId" ON "WorkflowExecutions" ("WorkflowId");
CREATE INDEX IF NOT EXISTS "IX_WorkflowExecutions_Status" ON "WorkflowExecutions" ("Status");
CREATE INDEX IF NOT EXISTS "IX_WorkflowExecutions_CreatedAt" ON "WorkflowExecutions" ("CreatedAt");

-- Create TaskExecutions table
CREATE TABLE IF NOT EXISTS "TaskExecutions" (
    "Id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "ExecutionId" uuid NOT NULL,
    "TaskId" uuid NOT NULL,
    "TaskName" varchar(200) NOT NULL,
    "Status" int NOT NULL DEFAULT 0,  -- 0=Pending, 1=Running, 2=Completed, 3=Failed, 4=Skipped
    "StartedAt" timestamp with time zone,
    "CompletedAt" timestamp with time zone,
    "Error" text,
    "Input" jsonb,
    "Output" jsonb,
    "RetryCount" int NOT NULL DEFAULT 0,
    CONSTRAINT "FK_TaskExecutions_WorkflowExecutions" 
        FOREIGN KEY ("ExecutionId") 
        REFERENCES "WorkflowExecutions" ("Id") 
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "IX_TaskExecutions_ExecutionId" ON "TaskExecutions" ("ExecutionId");
CREATE INDEX IF NOT EXISTS "IX_TaskExecutions_TaskId" ON "TaskExecutions" ("TaskId");
CREATE INDEX IF NOT EXISTS "IX_TaskExecutions_Status" ON "TaskExecutions" ("Status");

-- Create __EFMigrationsHistory table (required by Entity Framework)
CREATE TABLE IF NOT EXISTS "__EFMigrationsHistory" (
    "MigrationId" varchar(150) PRIMARY KEY,
    "ProductVersion" varchar(32) NOT NULL
);

-- Insert migration record
INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20251008000000_InitialCreate', '8.0.0')
ON CONFLICT DO NOTHING;

-- Grant permissions (adjust role name as needed)
GRANT ALL ON "WorkflowDefinitions" TO omarino_user;
GRANT ALL ON "WorkflowExecutions" TO omarino_user;
GRANT ALL ON "TaskExecutions" TO omarino_user;
GRANT ALL ON "__EFMigrationsHistory" TO omarino_user;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Scheduler service database schema created successfully!';
    RAISE NOTICE 'Tables: WorkflowDefinitions, WorkflowExecutions, TaskExecutions';
END $$;
