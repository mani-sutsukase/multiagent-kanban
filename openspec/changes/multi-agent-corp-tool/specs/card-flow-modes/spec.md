## ADDED Requirements

### Requirement: Swimlane supports auto flow mode
When a swimlane's flow_mode is "auto", the system SHALL automatically advance the card to the next swimlane after the Agent process exits successfully.

#### Scenario: Auto-flow after successful execution
- **WHEN** the Agent process exits with code 0 in an "auto" swimlane
- **THEN** the system SHALL set card status to "pending" in the next swimlane without user intervention

#### Scenario: Auto-flow stops on non-zero exit
- **WHEN** the Agent process exits with non-zero code
- **THEN** the system SHALL NOT advance the card and SHALL set card status to an error/blocked state

### Requirement: Swimlane supports pre-approval flow mode
When a swimlane's flow_mode is "pre_approval", the system SHALL advance the card to "waiting_approval" status after Agent execution, and SHALL NOT proceed until the user approves.

#### Scenario: Pre-approval waits for user
- **WHEN** the Agent process exits successfully in a "pre_approval" swimlane
- **THEN** the system SHALL set card status to "waiting_approval" and send a WebSocket notification

#### Scenario: Pre-approval advances on approve
- **WHEN** the user approves a card in "waiting_approval" status
- **THEN** the system SHALL set status to "approved" and advance to the next swimlane

### Requirement: Swimlane supports post-approval flow mode
When a swimlane's flow_mode is "post_approval", the system SHALL present the execution plan to the user before the Agent starts, and SHALL wait for confirmation to proceed.

#### Scenario: Post-approval shows plan before execution
- **WHEN** a card enters a "post_approval" swimlane
- **THEN** the system SHALL set card status to "waiting_approval" and the Agent SHALL generate a plan (without full execution)

#### Scenario: Post-approval executes on approve
- **WHEN** the user approves the plan in a "post_approval" swimlane
- **THEN** the system SHALL set card status to "running" and start the Agent process

### Requirement: User can reject with note and trigger re-execution
The system SHALL allow the user to reject a card with a text note, and the card SHALL re-enter "running" status in the same swimlane with the note attached.

#### Scenario: Reject with note
- **WHEN** the user rejects a card with note "数据来源需要更新，请使用最新的Q2数据"
- **THEN** the system SHALL save the rejection note, set card status to "running", and restart the Agent process with the note appended to the prompt

#### Scenario: Reject without note
- **WHEN** the user rejects a card without providing a note
- **THEN** the system SHALL return a validation error requiring a note

### Requirement: Card resumes session on re-execution
When a card is rejected and re-executed in the same swimlane, the system SHALL use the saved session_id to resume the Claude Code session, passing the rejection note as additional context.

#### Scenario: Resume on re-execution
- **WHEN** a card is rejected with note "拼写错误太多" and has a saved session_id
- **THEN** the system SHALL start claude.exe with --resume <session_id> flag and append the note to the prompt

#### Scenario: No session_id on first execution
- **WHEN** a card runs for the first time (no rejection history)
- **THEN** the system SHALL start claude.exe without --resume flag
