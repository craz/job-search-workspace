Feature: Keep private Codex history available inside the project

  Как разработчик, Я хочу синхронизировать относящиеся к проекту Codex-сессии,
  Чтобы продолжать работу по локальной истории без публикации приватных данных

  @story-ai-history-001
  Scenario: Synchronize an active project session safely
    Given Codex has project and unrelated session exports
    When the developer synchronizes AI history
    Then only the project session is linked inside the project
    And the derived view excludes reasoning and redacts credentials
    And the canonical Codex export remains unchanged

  @story-ai-history-002
  Scenario: Persist history when an agent response ends
    Given Codex and Cursor use the shared end-of-turn hook
    When either agent completes a response
    Then project history synchronization runs without blocking the response
    And a Cursor transcript supplied by the platform is linked without copying
