## ADDED Requirements

### Requirement: User can create a card in a board
The system SHALL allow the user to create a card with title, content, model, and target swimlane within a Kanban board.

#### Scenario: Create a card
- **WHEN** the user creates a card with title "生成Q2市场报告", content "请基于销售数据生成报告", model "claude-sonnet-4-20250514" in a specific swimlane
- **THEN** the system SHALL create the card with status "pending" in that swimlane

#### Scenario: Create a card without specifying a swimlane
- **WHEN** the user creates a card without specifying which swimlane
- **THEN** the system SHALL place the card in the first swimlane of the board

### Requirement: Card status machine
The system SHALL manage card status through a defined state machine: pending → running → waiting_approval → approved/rejected → completed. Each swimlane transition SHALL reset the card to pending in the next swimlane.

#### Scenario: Card moves to next swimlane after approval
- **WHEN** a card is approved in swimlane 1
- **THEN** the system SHALL create a new log for swimlane 2, set the card's current_swimlane_id to swimlane 2, and status to "pending"

#### Scenario: Card completes after last swimlane
- **WHEN** a card is approved in the last swimlane
- **THEN** the system SHALL set the card's status to "completed" and current_swimlane_id to null

### Requirement: User can view and delete cards
The system SHALL allow the user to view card details and delete cards.

#### Scenario: View card details
- **WHEN** the user requests a card by ID
- **THEN** the system SHALL return the card with all fields including current status and swimlane

#### Scenario: Delete a card
- **WHEN** the user deletes a card
- **THEN** the system SHALL remove the card and all associated logs and approvals

#### Scenario: Delete a running card
- **WHEN** the user deletes a card that is in "running" status
- **THEN** the system SHALL first terminate the associated claude.exe subprocess, then delete the card

### Requirement: Card carries session_id and rejection_note
The system SHALL persist the Claude Code session_id on each card and the latest rejection note for resume functionality.

#### Scenario: Session ID saved after agent execution
- **WHEN** an Agent process starts for a card
- **THEN** the system SHALL save the session_id to the card record

#### Scenario: Rejection note saved
- **WHEN** an approval action rejects the card
- **THEN** the system SHALL save the rejection note to the card record
