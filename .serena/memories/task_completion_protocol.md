# Task Completion Protocol

When you have completed a coding task, follow these steps to ensure quality and consistency:

1.  **Format Code**: Run `make format` to ensure the code adheres to the project's style guidelines (Black).
2.  **Lint Code**: Run `make lint` to check for any linting errors (Ruff) and type issues (Mypy). Fix any issues found.
3.  **Run Tests**: Run `make test` to ensure that your changes haven't broken existing functionality.
4.  **Add Tests**: If you added new functionality, ensure you have added corresponding tests in the `tests/` directory.
5.  **Verify**: If possible, verify the changes manually or by running the server (`make run`) if applicable.

Only after these steps are successfully completed should you consider the task done.
