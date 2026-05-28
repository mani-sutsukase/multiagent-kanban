## ADDED Requirements

### Requirement: System starts claude.exe subprocess for card execution
The system SHALL start a `claude.exe` CLI subprocess for each card that enters "running" status, passing the configured prompt, skill, model, and session_id (if applicable) as arguments.

#### Scenario: Start claude.exe with all parameters
- **WHEN** a card enters "running" status in a swimlane with prompt "撰写报告" and model "claude-sonnet-4-20250514"
- **THEN** the system SHALL start claude.exe with arguments including -p "撰写报告" and --model "claude-sonnet-4-20250514"

#### Scenario: Start claude.exe with skill
- **WHEN** the swimlane has a skill "write-draft" configured
- **THEN** the system SHALL include --skill "write-draft" in the claude.exe arguments

#### Scenario: Start claude.exe with session resume
- **WHEN** the card was rejected and has session_id "abc123"
- **THEN** the system SHALL include --resume "abc123" in the claude.exe arguments

### Requirement: System supports parallel subprocess execution
The system SHALL allow multiple claude.exe subprocesses to run concurrently, controlled by a configurable concurrency limit.

#### Scenario: Process pool respects max concurrency
- **WHEN** there are 5 cards queued and max_concurrency is set to 3
- **THEN** the system SHALL start at most 3 concurrent claude.exe processes

#### Scenario: Process starts when slot frees up
- **WHEN** one of the 3 running processes finishes
- **THEN** the system SHALL start the next queued card's process

### Requirement: System captures subprocess output in real-time
The system SHALL capture stdout and stderr from the claude.exe subprocess, stream them to the logs table, and push them to the frontend via WebSocket.

#### Scenario: Stdout captured and persisted
- **WHEN** the claude.exe process outputs a line to stdout
- **THEN** the system SHALL append that line to the log record and send it via WebSocket

#### Scenario: Stderr captured separately
- **WHEN** the claude.exe process outputs to stderr
- **THEN** the system SHALL capture it separately from stdout in the log record

### Requirement: System saves Claude Code session_id
The system SHALL extract and save the Claude Code session_id from the subprocess for later resume use.

#### Scenario: Session ID saved after process start
- **WHEN** a claude.exe process starts
- **THEN** the system SHALL capture the session_id from the process (via environment or output parsing) and save it to the card record

### Requirement: System handles subprocess lifecycle
The system SHALL monitor subprocess lifecycle including normal exit, crash, and forced termination.

#### Scenario: Process exits normally
- **WHEN** the claude.exe process exits with code 0
- **THEN** the system SHALL record the exit code and trigger the card flow decision

#### Scenario: Process crashes
- **WHEN** the claude.exe process exits with non-zero code
- **THEN** the system SHALL record the exit code and stderr, and set card status to a blocked/error state

#### Scenario: Card deleted while running
- **WHEN** a card is deleted while its claude.exe process is running
- **THEN** the system SHALL terminate the subprocess and clean up
