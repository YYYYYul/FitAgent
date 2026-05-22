1. # CLAUDE.md

   This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

   # FitAgent

   FitAgent is an enterprise-style task-oriented fitness Agent project designed to demonstrate real-world Agent engineering capability for job seeking.

   The project is NOT:
   - a generic chatbot
   - a traditional CRUD fitness app
   - a pure RAG demo
   - a social/gamification platform

   The project IS:
   - an Agent workflow project
   - a Tool Calling project
   - a Plan-Execute-Replan system
   - a long-term memory Agent system
   - a business closed-loop AI application

   ---

   # Core Business Scope

   FitAgent only focuses on:

   1. casual chat
   2. fitness knowledge Q&A via RAG
   3. training plan generation
   4. weekly recurring reminders
   5. workout logging
   6. calendar review and history query
   7. plan adjustment and reminder synchronization

   Keep the scope focused.

   ---

   # Non-Goals

   Do NOT implement:

   - diet systems
   - calorie tracking
   - camera/video posture correction
   - medical diagnosis
   - injury rehabilitation
   - automatic training escalation
   - voice assistant systems
   - social/community systems
   - overly complex multi-agent systems
   - unnecessary AI features

   Avoid feature creep.

   ---

   # Tech Stack

   | Layer           | Tech                                               |
   | --------------- | -------------------------------------------------- |
   | Frontend        | Next.js + TypeScript + Tailwind CSS + FullCalendar |
   | Backend         | Python FastAPI                                     |
   | Agent Framework | LangGraph (StateGraph)                             |
   | Database        | PostgreSQL + pgvector                              |
   | Cache           | Redis                                              |
   | Scheduler       | APScheduler (MVP)                                  |
   | RAG             | pgvector + text-embedding-3-small                  |

   ---

   # Current Development Stage

   Current stage: **MVP Phase**

   Current MVP goal:

   Run the minimal business closed-loop:

   User Input
   → Generate Plan
   → Save Plan
   → Log Workout
   → Query Calendar / History

   Do NOT over-engineer the MVP.

   ---

   # Core Architecture

   User Input
   → FastAPI API Gateway
   → LangGraph Agent
   → Intent Router
   → Intent Node
   → Tool Calling / RAG
   → Agent Trace Logger
   → PostgreSQL

   Intent types:

   - casual_chat
   - fitness_qa
   - create_plan
   - update_plan
   - log_workout
   - query_history

   ---

   # Mandatory Architecture Rules

   The project MUST follow:

   - Intent Router architecture
   - Tool Calling architecture
   - Plan-Execute-Replan workflow
   - Long-term state persistence
   - Agent Trace logging
   - Explicit business workflow

   Do NOT bypass the Agent workflow.

   Do NOT replace Tool Calling with pure LLM responses.

   ---

   # Plan-Execute-Replan Rules

   Task execution MUST follow:

   Plan
   → Execute
   → Observe
   → Replan

   ## Plan

   Responsible for:
   - identifying user goals
   - checking required information
   - deciding required tools
   - deciding whether RAG is needed
   - generating execution steps

   ## Execute

   Responsible for:
   - Tool Calling
   - RAG retrieval
   - database writes
   - reminder operations

   ## Observe

   Responsible for:
   - checking tool execution success
   - checking DB write success
   - checking reminder creation success
   - validating business rules

   ## Replan

   Trigger when:
   - user information is incomplete
   - active plan does not exist
   - tool execution fails
   - reminder creation fails
   - user changes training rhythm
   - repeated missed workouts
   - workflow becomes invalid

   ---

   # Intent Router Rules

   Routing strategy:

   1. LLM classification (primary)
   2. keyword fallback (confidence < 0.7)

   If routing is uncertain:
   → fallback to casual_chat

   Do NOT add unnecessary intents.

   ---

   # RAG Rules

   RAG is ONLY used for:
   - fitness knowledge Q&A

   RAG is NOT used for:
   - casual chat
   - plan generation
   - workout logging
   - reminder scheduling

   Knowledge base categories:
   - beginner principles
   - fat loss basics
   - muscle gain basics
   - full body training
   - PPL training
   - home workouts
   - gym exercises
   - recovery basics
   - training frequency
   - common mistakes

   Do NOT include:
   - medical diagnosis
   - dangerous advice
   - drug recommendations

   ---

   # Core Tools

   The MVP only supports THREE tools:

   ## 1. generate_training_plan

   Input:
   - user profile
   - goal
   - weekly days
   - training location
   - experience level

   Output:
   - structured weekly plan JSON

   ---

   ## 2. create_weekly_reminder

   Input:
   - plan_id
   - training days
   - reminder time
   - channel

   Output:
   - reminder jobs

   MVP:
   only persist reminder jobs in DB.

   Real APScheduler push comes later.

   ---

   ## 3. log_workout_record

   Input:
   - raw workout text

   Output:
   - structured workout JSON
   - saved workout log

   Use LLM structured parsing.

   ---

   # Long-Term Memory Rules

   Persist:
   - user profile
   - active plan
   - reminder jobs
   - workout history
   - calendar state
   - agent traces

   The Agent must maintain continuity across sessions.

   ---

   # Agent Trace Rules

   Every conversation SHOULD log:

   - user input
   - detected intent
   - plan steps
   - tools called
   - tool results
   - replan reasons
   - final response

   Traceability is important.

   ---

   # Database Rules

   Core tables:

   - user_profile
   - training_plan
   - reminder_job
   - workout_log
   - agent_trace
   - knowledge_chunks

   Each user can only have ONE active training plan.

   Use partial unique index.

   ---

   # Development Priorities

   Priority order:

   1. business closed-loop
   2. workflow correctness
   3. tool correctness
   4. stable architecture
   5. clean modular code
   6. extensibility

   Do NOT prioritize:
   - fancy UI
   - premature optimization
   - excessive abstractions
   - advanced infrastructure too early

   ---

   # MVP Scope

   MVP MUST include:

   - chat interface
   - intent router
   - generate plan tool
   - log workout tool
   - basic reminder persistence
   - workout history query
   - calendar view
   - agent trace logging

   MVP does NOT require:

   - MCP
   - Celery
   - advanced observability
   - multi-agent systems
   - complex auth systems
   - production deployment

   ---

   # MCP Strategy

   MCP is NOT required during MVP.

   Development stages:

   Stage 1:
   Use normal function calling.

   Stage 2:
   Stabilize workflow and tools.

   Stage 3:
   Refactor tools into MCP Server.

   MCP should expose:
   - tools
   - resources
   - prompts

   Do NOT over-engineer MCP early.

   ---

   # Skills Strategy

   Skills are ONLY used for:
   - workflow guidance
   - prompt templates
   - behavioral instructions

   Skills are NOT execution tools.

   Business execution MUST happen through Tool Calling.

   ---

   # Human-in-the-Loop Rules

   Require user confirmation before:

   - regenerating full plans
   - deleting workout records
   - changing long-term reminders
   - major training intensity changes

   Never perform high-impact actions silently.

   ---

   # Code Quality Rules

   All code should be:

   - modular
   - typed
   - maintainable
   - production-structured
   - explicit in business logic

   Avoid:
   - giant files
   - hidden state mutations
   - tightly coupled modules
   - magic prompts
   - unnecessary frameworks

   ---

   # Common Commands

   ## Backend

   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   
   alembic upgrade head
   
   pytest tests/ -v
   pytest tests/ -v -k "test_tool"

---

# Code Comment Rules

Comments must be **necessary and explanatory** — they must help a developer (or your future self) understand the system without AI assistance.

## What MUST be commented

- **Agent Workflow**: Each LangGraph node must have a brief docstring describing its input, output, and responsibility
- **Intent Router**: The routing strategy (LLM primary + keyword fallback) must be explained at the module level
- **Tool Calling**: Each tool function must document its input schema, output schema, and internal steps
- **Plan-Execute-Replan**: Each phase (Plan / Execute / Observe / Replan) must have a flow-level comment
- **RAG retrieval logic**: The retrieval pipeline (embed → search → rerank → context assembly) must be documented
- **State transitions**: AgentState field changes across nodes must be traceable via comments
- **Key business judgments**: BMI warnings, frequency checks, intensity validations — explain WHY the threshold exists
- **Guardrails**: Each blocked pattern or validation rule must have a reason comment
- **Fallback logic**: Every fallback path (keyword fallback, error fallback, empty result fallback) must be explained
- **Agent Trace**: What is logged, when, and why — must be documented

## What must NOT be commented

- Code that is self-explanatory from well-named identifiers
- Every single line of obvious logic
- Parameter descriptions that repeat the type annotation
- Change logs or "added by" markers in source files
- TODO comments without a clear action and reason

## Format

- Module-level docstrings: 2-4 lines describing the module's role in the Agent workflow
- Function docstrings: 1-2 lines for simple functions; for tool functions, include Input/Output/Steps
- Inline comments: use only for non-obvious decisions (the WHY, not the WHAT)
- Node docstrings must follow the pattern: `"""Node: [name] — [one-line responsibility]. In: [key state fields]. Out: [key state fields]."""`

---

# Documentation Maintenance Rules

After completing each development phase, the following documents MUST be updated to reflect the current code state. Code is not considered "done" until the documentation is synchronized.

## README.md

Must always reflect:
- Project purpose and current capabilities
- Complete tech stack
- How to run the project (backend + frontend + database)
- API examples for core endpoints
- Architecture diagram (text or Mermaid)
- Current development phase and progress
- Link to demo script

Update trigger: after any phase completion.

## TASKS.md

Must always reflect:
- Current phase name and goal
- Completed tasks (checked off)
- In-progress tasks with current status
- Pending tasks for the next phase
- Current blockers and their impact
- Next phase preview

Update trigger: any time a task is started, completed, or blocked.

## Phase completion checklist

Before declaring a phase complete:
1. [ ] README.md updated
2. [ ] TASKS.md updated
3. [ ] All tests pass
4. [ ] Agent Trace logging verified for all intent types
5. [ ] Demo script covers all new features
6. [ ] No stale comments or dead code from previous phase
