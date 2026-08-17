Feature: Reproduce the Job Search workspace

  As a developer working with the system
  I want to obtain and validate the compatible repositories from one workspace
  So that I can start development from a known reproducible state

  @story-workspace-001
  Scenario: Initialize a missing service submodule
    Given a service gitlink is recorded but its checkout is absent
    When the developer runs workspace bootstrap
    Then bootstrap initializes the exact recorded service revision

  @story-workspace-001
  Scenario: Validate submodules that are already initialized
    Given all submodules recorded by the workspace exist locally
    When the developer runs workspace bootstrap
    Then bootstrap preserves every existing submodule revision
    And reports no submodule errors

  @story-workspace-001
  Scenario: Validate the workspace without network access
    Given local submodule commits match the workspace gitlinks
    When the developer runs doctor in offline mode
    Then all local repository checks pass

  @story-workspace-002
  Scenario: Apply infrastructure naming when creating a service instance
    Given the workspace contains the canonical naming convention and USED registry
    When Codex or Cursor creates a long-lived service instance
    Then its instructions require a free class-appropriate canonical slug
    And ordinary Compose services remain functionally named
