## ADDED Requirements

### Requirement: User can create a Kanban board
The system SHALL allow the user to create a Kanban board with a name and optional description.

#### Scenario: Create a Kanban board
- **WHEN** the user submits a new Kanban form with name "内容审核" and description "用于审核内容的流水线"
- **THEN** the system SHALL create a new board and return its ID, name, description, and timestamps

#### Scenario: Create a Kanban board with empty name
- **WHEN** the user submits a new Kanban form with an empty name
- **THEN** the system SHALL return a validation error

### Requirement: User can edit and delete a Kanban board
The system SHALL allow the user to update the name/description of a Kanban board and delete a board (cascading delete all swimlanes and cards).

#### Scenario: Edit Kanban board
- **WHEN** the user updates the Kanban name to "内容审核v2"
- **THEN** the system SHALL update the board and return the new data

#### Scenario: Delete Kanban board
- **WHEN** the user deletes a Kanban board
- **THEN** the system SHALL remove the board and all associated swimlanes, cards, logs, and approvals

### Requirement: User can list all Kanban boards
The system SHALL provide a list of all Kanban boards with their basic info.

#### Scenario: List Kanban boards
- **WHEN** the user requests the Kanban list
- **THEN** the system SHALL return all boards sorted by creation time

### Requirement: User can configure swimlanes on a board
The system SHALL allow the user to add, edit, delete, and reorder swimlanes within a Kanban board. Each swimlane SHALL have: name, sort_order, prompt, optional skill, tools list, and flow_mode.

#### Scenario: Add a swimlane
- **WHEN** the user adds a swimlane "初稿生成" with flow_mode "auto" to a board
- **THEN** the system SHALL create the swimlane at the end of the swimlane list

#### Scenario: Edit a swimlane
- **WHEN** the user changes the swimlane's prompt to "你是内容撰写专家..."
- **THEN** the system SHALL update the swimlane's prompt

#### Scenario: Delete a swimlane
- **WHEN** the user deletes a swimlane that has no running cards
- **THEN** the system SHALL remove the swimlane

#### Scenario: Delete a swimlane with running cards
- **WHEN** the user deletes a swimlane that has cards in "running" status
- **THEN** the system SHALL return an error and prevent deletion

#### Scenario: Reorder swimlanes
- **WHEN** the user submits a new order of swimlane IDs
- **THEN** the system SHALL update all swimlanes' sort_order values
