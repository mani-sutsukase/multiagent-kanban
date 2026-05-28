## ADDED Requirements

### Requirement: User can create a scheduled task
The system SHALL allow the user to create a scheduled task with a cron expression, a card template (title, content, model), and a target Kanban board + swimlane.

#### Scenario: Create a daily scheduled task
- **WHEN** the user creates a schedule with cron "0 9 * * *", title "日报生成", content "请生成今日工作日报", model "claude-sonnet-4-20250514", targeted at a specific board's first swimlane
- **THEN** the system SHALL register the cron job and persist the schedule to the database

#### Scenario: Create a weekly scheduled task
- **WHEN** the user creates a schedule with cron "0 9 * * 1" (every Monday)
- **THEN** the system SHALL register the cron job to fire every Monday at 9:00

#### Scenario: Invalid cron expression
- **WHEN** the user submits a schedule with an invalid cron expression "not-a-cron"
- **THEN** the system SHALL return a validation error

### Requirement: Scheduled task creates a card on trigger
When a scheduled task fires, the system SHALL create a new card using the task's template and place it in the configured board + swimlane.

#### Scenario: Card created on schedule trigger
- **WHEN** the cron expression "0 9 * * *" fires
- **THEN** the system SHALL create a new card with the template's title, content, and model in the target board and swimlane

#### Scenario: Schedule log recorded
- **WHEN** a scheduled task triggers and creates a card
- **THEN** the system SHALL record the trigger in the schedule_logs table with the created card_id and status "success"

### Requirement: User can toggle scheduled task on/off
The system SHALL allow the user to enable or disable a scheduled task without deleting it.

#### Scenario: Disable a schedule
- **WHEN** the user disables a schedule
- **THEN** the system SHALL remove the cron job from APScheduler without deleting the schedule record

#### Scenario: Enable a schedule
- **WHEN** the user re-enables a disabled schedule
- **THEN** the system SHALL re-register the cron job

### Requirement: User can view scheduled task execution history
The system SHALL display the execution history for each scheduled task, showing when each trigger fired and what card was created.

#### Scenario: View schedule history
- **WHEN** the user views the execution history of a schedule
- **THEN** the system SHALL list all trigger events with timestamps, created card IDs, and status

#### Scenario: Failed schedule execution
- **WHEN** a scheduled task fires but card creation fails
- **THEN** the system SHALL record the trigger with status "failed" and the error message

### Requirement: Scheduled tasks persist across application restarts
The system SHALL reload all enabled scheduled tasks from the database on application startup.

#### Scenario: Reload schedules on startup
- **WHEN** the application starts
- **THEN** the system SHALL read all schedules with enabled=1 from the database and register them with APScheduler
