**Purpose**
- Capture the current auto‑routing design so future edits keep natural outputs and the LLM‑first philosophy for tool arguments.
- Scope: `CoE-Backend` (chat entrypoints, agent nodes, tool dispatcher, tools, LangFlow execution).

**High‑Level Flow**
- Client hits `POST /v1/chat/completions` → `api/chat_api.py` builds `AgentState` and calls agent.
- Agent node `core/agent_nodes.py::tool_dispatcher_node` tries auto‑routing first, then falls back to normal tool calling.
- Auto-routing core lives in `services/tool_dispatcher.py`:
  - Description/text and LLM strategies now return **suggestions** rather than executing tools directly.
  - Suggestions capture the tool name, optional flow metadata, and recommended arguments.
  - `core/agent_nodes.py` injects a one-off system hint and forces the primary LLM to issue the actual `tool_call`, preserving the canonical tool-request trace.

**Design Principles**
- LLM-first arguments: Do NOT regex-parse user text for tool args. Let the LLM infer arguments from the tool’s JSON schema.
- Preserve tool requests: even when auto-routing fires, the final `tool_call` must originate from the LLM so clients see a consistent history.
- Natural output: Never return raw dumps to end users. Show the essential human-readable message only.
- Separation of concerns: Tools compute; dispatchers orchestrate; formatters shape the final message.
- Reversible routing: `AUTO_ROUTE_STRATEGY` controls whether auto-routing is used (see Configuration).
- Client directives first: if the incoming request includes `tool_choice`, the agent honors that instruction before attempting any auto-routing.

**Key Modules**
- `services/tool_dispatcher.py`
  - `_format_flow_outputs_for_chat(outputs)`: extracts a single natural message from LangFlow results (no raw).
  - `maybe_execute_best_tool_by_description(...)` / `maybe_execute_best_tool_by_llm(...)`: return structured suggestions (`tool_name`, optional `arguments`, flow metadata) without executing the tool.
- `services/langflow/langflow_service.py`
  - Executes LangFlow graphs across versions, normalizes outputs, and returns `ExecuteFlowResponse`.
  - Avoids exposing `raw` to end users; dispatcher formats final text.
- `core/agent_nodes.py::tool_dispatcher_node`
  - Tries auto‑routing first; if not decisive, falls back to standard tool calling with the model.

**Configuration**
- `AUTO_ROUTE_STRATEGY`: `llm` (default) | `text` | `off`
  - `llm`: LLM picks a tool/flow. If none, optionally fall back to text strategy depending on `AUTO_ROUTE_LLM_FALLBACK`.
  - `text`: keyword heuristic only; still formats outputs naturally.
  - `off`: skip proactive auto‑routing; rely on the model’s own tool_calls.
- `AUTO_ROUTE_LLM_FALLBACK`: `false` (default) | `true`
  - When `AUTO_ROUTE_STRATEGY=llm` and this is `false`, the dispatcher will not attempt keyword/text fallback. This enforces strict “LLM‑only” routing.
- `AUTO_ROUTE_MODEL`: model used for LLM routing and argument generation (default `gpt-4o-mini`).

**Group Filtering (optional)**
- Request can include `group_name` (already flows through to `AgentState`).
- Python tools: `get_available_tools_for_context(context, group_name)` filters by an optional `allowed_groups: List[str]` exported by each `*_map.py`. If `allowed_groups` is absent, the tool is visible to all groups.
- LangFlow flows: `_flow_allowed_in_context` accepts `group_name` and also permits a mapping row where `context` is `"{context}:{group_name}"` (no DB migration needed). To restrict a flow to a group, add a row in `langflow_tool_mappings` with a composite context like `aider:dev-team`.

**Tool Contract (Python)**
- Location: `tools/*_tool.py` and `*_map.py` (schema registration).
- Schema: export `available_tools: List[Dict]` with `{"type":"function","function":{"name","description","parameters"}}`.
- Functions: export `tool_functions: Dict[str, callable]` and an async `run(tool_input, state)`.
- Return shape: `{"messages":[{"role":"assistant","content":"..."}]}` to let dispatcher surface content naturally.
- Do not parse the user’s free text inside the tool; assume LLM supplies arguments.

**Output Rules**
- Do NOT prefix with status banners (e.g., "✅ 자동 라우팅...").
- Success: return only the natural language content string.
- Error: concise sentence (e.g., "도구 실행 중 오류가 발생했습니다: <detail>").
- LangFlow: `_format_flow_outputs_for_chat` ensures a single, readable sentence.

**Anti‑Patterns (Avoid)**
- Regex or ad‑hoc parsing in dispatcher or tools for argument extraction.
- Returning raw dictionaries or verbose debug blobs to users.
- Mixing routing banners with user‑visible responses.

**When Extending**
- New tool: define a clear JSON schema with required fields; keep `run` pure; return messages shape.
- New LangFlow flow: ensure descriptions are meaningful for candidate selection; rely on dispatcher formatting.
- Changing models: if argument inference becomes flaky, revisit tool descriptions/JSON schemas or upgrade `AUTO_ROUTE_MODEL` so the forced tool call still succeeds.

**Quick Tests**
- LangFlow path: ask a flow‑intent query → response should be a clean sentence (no raw).
- Python tool path: issue a query that implies a tool with parameters → the LLM should pick it and fill arguments; response is a clean sentence.

**Troubleshooting**
- If arguments are missing: inspect LLM routing logs and the tool schema; the LLM might need a stricter description/parameters.
- If raw leaks: verify changes still route final text through `_format_flow_outputs_for_chat` or `_format_tool_result_for_chat`.
