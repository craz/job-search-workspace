Feature: Reproduce the Job Search workspace

  As a developer working with the system
  I want to obtain and validate the compatible repositories from one workspace
  So that I can start development from a known reproducible state

  @story-workspace-001
  Scenario: Validate repositories that are already present
    Given all repositories from the lock file exist locally
    When the developer runs workspace bootstrap
    Then bootstrap preserves every existing repository
    And reports no repository errors

  @story-workspace-001
  Scenario: Validate the workspace without network access
    Given local repository commits match the lock file
    When the developer runs doctor in offline mode
    Then all local repository checks pass
