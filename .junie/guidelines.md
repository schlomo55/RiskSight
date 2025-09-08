# 🧠 General Software Design and Implementation Guidelines

This document defines **rules and expectations** for how any software development task should be approached.  
It ensures results are well-designed, efficient, testable, secure, and maintainable — regardless of programming language or tech stack.

---

## 📌 Overview

- **Applies to**: Any software project (backend, frontend, CLI, APIs, data pipelines, embedded, systems, etc.)
- **Goals**: Correctness, modularity, maintainability, performance, testability, and security
- **Style**: Language-agnostic, OOP-first, performance-aware, secure-by-default

---

## 🛠️ Process

1. **Analyze the task requirements** carefully.  
2. **Break down the system** into logical components or modules.  
3. **Propose a high-level design** (architecture, classes, modules) before coding.  
4. **Ask clarifying questions** before proceeding if any part of the task is ambiguous.  
5. **Use diagrams** (e.g., UML class or flow diagrams) when helpful for complex systems.  

---

## 🧱 Design Principles

- Use **Object-Oriented Programming (OOP)** where appropriate.  
- Follow core engineering principles: **SOLID**, **DRY**, **KISS**, **YAGNI**.  
- Apply design patterns **only when they simplify or clarify the design**.  
- Maintain clear **separation of concerns**: domain logic, infrastructure, interfaces, utilities/helpers.  
- Prefer **explicit over implicit** design choices.  

---

## 💻 Code Expectations

- Use **idiomatic, clean, and secure code** for the chosen language.  
- Organize code into logical files or modules.  
- Prioritize **readability and clarity** with:
  - Self-explanatory variable/method names  
  - **Docstrings** or API-level documentation for all public classes/methods  
  - **Inline comments** for complex logic or edge-case handling  
- Ensure the code is:
  - Fully functional and directly executable  
  - Free of placeholders or TODOs  
  - Handles errors and exceptions gracefully  
- Validate and sanitize all external inputs.  
- Follow secure coding practices to prevent vulnerabilities (e.g., injection, unsafe parsing).  

### 📄 Logging Requirements

- Every system **must create an external log for each run**.  
- Maintain **two separate log files**:
  - `general.log` for informational and debug-level messages  
  - `error.log` for errors, exceptions, and stack traces  
- Log entries must include:
  - ISO-8601 timestamp  
  - Log level (`INFO`, `DEBUG`, `ERROR`, etc.)  
  - Contextual message  
- All logs must be:
  - Written to persistent files (e.g., under a `/logs` directory)  
  - Structured and human-readable  
  - Rotated or archived based on size or date if long-running  
- Prefer using the language’s standard or widely accepted logging libraries.  
- Logging behavior should be encapsulated in a dedicated class or service (e.g., `ILogger`, `FileLogger`).  

### ✍️ Naming and Coding Conventions

- **Constants**: `ALL_CAPS_WITH_UNDERSCORES` (e.g., `MAX_TIMEOUT`)  
- **Methods & Variables**: `camelCase` (e.g., `calculateTotal`)  
- **Booleans**: Use positive, descriptive names (e.g., `isActive`)  
- **File Naming**: Match file names with main class/module (e.g., `UserService.py`)  
- **Avoid Abbreviations** unless well-known (`URL`, `ID`, `API`)  
- **Comments**: Document **why** something is done, not just **what** it does  

### 🔍 Performance & Efficiency

- Optimize for:
  - ✅ Time complexity  
  - ✅ Space complexity  
  - ✅ Runtime efficiency  
  - ✅ Memory usage  
- Avoid:
  - Inefficient loops  
  - Redundant operations  
  - Unnecessary memory allocations  

---

## 🧩 Output Structure

1. **High-Level Design** – Architecture summary or diagram  
2. **Implementation Code** – Organized by file/module/class with documentation  
3. **Instructions Document** – How to build, run, and test the solution  
4. **Task Description Document** – Human-readable explanation of the task’s purpose, scope, and requirements  
5. **How-to-Run Document** – Setup steps, dependencies, and commands  
6. **Task Explanation Document** – Plain-language summary of inputs, outputs, and use cases  
7. **Usage Examples** – Snippets to demonstrate key components  

---

## 🔧 Tooling & Automation

- Use linters and formatters (e.g., ESLint, Black, Prettier, Pylint).  
- Consider setting up a **CI/CD pipeline** to:
  - Run tests  
  - Lint/format codebase  
  - Check code coverage  

---

## 📣 Rules of Engagement

- If the task is **unclear**, always ask clarifying questions.  
- Avoid vague or ambiguous solutions.  
- All **non-obvious logic**, **complex conditions**, and **public APIs** must be **commented or documented**.  
- Always produce a **self-contained**, directly executable solution that passes its tests.  
- Document the use of any **design patterns** with a short rationale.  
- Strive for the **best balance of performance, clarity, security, and maintainability**.  

---

## 📂 Required Project Documentation Files

1. **`architecture.md`** – System design & class structure (include diagrams)  
2. **`task_list.md`** – Development task checklist with progress tracking  
3. **`how_it_works.md`** – Plain-language description of how the system works  

> 🔁 These documents must always be kept up to date alongside code changes.  
