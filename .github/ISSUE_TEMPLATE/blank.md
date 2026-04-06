name: 📝 Blank Issue
description: Create a blank issue for tracking tasks, questions, or discussions
body:
  - type: markdown
    attributes:
      value: |
        > ⚠️ For bugs, use the **Bug Report** template. For features, use **Feature Request**.

  - type: input
    id: title
    attributes:
      label: Title
    validations:
      required: true

  - type: textarea
    id: body
    attributes:
      label: Description
      description: Describe the task, question, or topic.
    validations:
      required: true
