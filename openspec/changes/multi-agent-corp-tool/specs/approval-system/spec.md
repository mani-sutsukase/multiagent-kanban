## ADDED Requirements

### Requirement: User can view all pending approvals
The system SHALL display all cards in "waiting_approval" status across all Kanban boards in a unified approval panel.

#### Scenario: View pending approvals
- **WHEN** the user opens the approval panel
- **THEN** the system SHALL list all cards with status "waiting_approval", grouped by board

#### Scenario: No pending approvals
- **WHEN** there are no cards in "waiting_approval" status
- **THEN** the system SHALL display an empty state message

### Requirement: User can view Agent execution logs during approval
The system SHALL allow the user to view the full stdout/stderr of the Agent's execution for the current swimlane when making an approval decision.

#### Scenario: View logs in approval panel
- **WHEN** the user clicks on a pending approval card
- **THEN** the system SHALL display the Agent's stdout and stderr for that swimlane's execution

#### Scenario: Logs update in real-time
- **WHEN** the Agent is still running in a "post_approval" mode
- **THEN** the system SHALL stream new log lines via WebSocket as they are produced

### Requirement: User can approve a card
The system SHALL allow the user to approve a card, which advances it to the next swimlane.

#### Scenario: Approve a card
- **WHEN** the user clicks "Approve" on a card in "waiting_approval" status
- **THEN** the system SHALL create an approval record with action "approved" and advance the card to the next swimlane

### Requirement: User can reject a card with a note
The system SHALL require the user to provide a text note when rejecting a card, and SHALL restart the card in the same swimlane.

#### Scenario: Reject a card with note
- **WHEN** the user clicks "Reject" and provides note "数据需要更新"
- **THEN** the system SHALL create an approval record with action "rejected" and note "数据需要更新", save the note to the card, and restart the card in the current swimlane

#### Scenario: Reject without note is rejected
- **WHEN** the user clicks "Reject" without providing a note
- **THEN** the system SHALL show a validation error requiring a note

### Requirement: User receives real-time notification for new approvals
The system SHALL push notifications to the frontend via WebSocket when a card enters "waiting_approval" status.

#### Scenario: WebSocket notification on new approval needed
- **WHEN** a card's status changes to "waiting_approval"
- **THEN** the system SHALL send a WebSocket event of type "card_needs_approval" to the frontend

#### Scenario: Badge count updates
- **WHEN** a new card enters "waiting_approval" status
- **THEN** the approval panel's badge count SHALL increment in real-time
