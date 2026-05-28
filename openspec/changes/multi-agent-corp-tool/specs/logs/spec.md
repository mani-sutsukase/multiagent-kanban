## ADDED Requirements

### Requirement: System records execution log for each swimlane attempt
The system SHALL create a log entry every time a card enters "running" status in a swimlane, recording attempt number, process ID, timestamps, and session_id.

#### Scenario: Log created on execution start
- **WHEN** a card starts running in a swimlane
- **THEN** the system SHALL create a log record with card_id, swimlane_id, attempt number, process_id, started_at, and session_id

#### Scenario: Log completed on execution end
- **WHEN** the claude.exe process exits
- **THEN** the system SHALL update the log with finished_at, exit_code, and complete stdout/stderr

#### Scenario: Attempt number increments on reject
- **WHEN** a card is rejected and re-executes in the same swimlane
- **THEN** the system SHALL create a new log with attempt = previous_attempt + 1

### Requirement: System streams live logs during execution
The system SHALL stream log output to the frontend in real-time via WebSocket while the Agent process is running.

#### Scenario: Live log streaming
- **WHEN** a card is in "running" status and the Agent produces output
- **THEN** the system SHALL send WebSocket events of type "card_log_update" with new log content

#### Scenario: Multiple clients receive the same log stream
- **WHEN** multiple browser tabs are open to the same card
- **THEN** all tabs SHALL receive the same log stream events

### Requirement: User can view historical execution timeline
The system SHALL display the complete execution history of a card, showing each swimlane it passed through with all attempts.

#### Scenario: View card execution timeline
- **WHEN** the user opens a completed card's detail
- **THEN** the system SHALL show a timeline of all swimlanes the card passed through, with start/finish times for each

#### Scenario: View swimlane history with multiple attempts
- **WHEN** a card was rejected and re-executed in a swimlane
- **THEN** the timeline SHALL show all attempts for that swimlane with their individual logs

### Requirement: User can view complete stdout/stderr
The system SHALL allow the user to view the full stdout and stderr content of any log entry.

#### Scenario: View stdout
- **WHEN** the user clicks on a log entry's stdout tab
- **THEN** the system SHALL display the full stdout content with proper formatting

#### Scenario: View stderr
- **WHEN** the user clicks on a log entry's stderr tab
- **THEN** the system SHALL display the full stderr content

#### Scenario: Large log content
- **WHEN** the log content exceeds 10,000 characters
- **THEN** the system SHALL still display the full content with scroll
