# Beaver's Choice Paper Company — Multi‑Agent Inventory + Quoting System

This project implements a **text‑in / text‑out** multi‑agent workflow for Beaver's Choice Paper Company to:

- answer inventory questions,
- generate quotes using catalog + historical quote context,
- finalize sales by recording transactions in an SQLite database,
- evaluate performance over a batch of sample customer requests.

The implementation uses **smolagents** (`ToolCallingAgent`) and an SQLite database (`munder_difflin.db`) managed via **SQLAlchemy + pandas**.

---

## What’s in this repo

- `project_starter.py` — single‑file implementation (database helpers, tools, agents, evaluation runner)
- `workflow_diagram.md` — workflow diagram (Mermaid) showing agents, tools, and data flow
- `quote_requests_sample.csv` — evaluation dataset (batch of customer requests)
- `quote_requests.csv` — full request dataset used to seed the database
- `quotes.csv` — historical quotes used for quote‑history lookup
- `test_results.csv` — generated output after running the evaluation (created by `project_starter.py`)
- `requirements.txt` — Python dependencies (see notes below)

---

## Architecture (max 5 agents)

The system is designed around an **orchestrator + specialist worker agents**. In code, the following agent classes exist:

1. **`OrchestrationAgent`** (orchestrator)
   - Customer‑facing entrypoint.
   - Parses the request and coordinates inventory checks, quote generation, and (if applicable) sale finalization.
2. **`InventoryAgent`** (worker)
   - Stock questions (per‑item or full snapshot).
   - Flags reorder needs based on `min_stock_level`.
3. **`QuotingAgent`** (worker)
   - Produces customer‑facing quotes using catalog pricing, inventory availability, and historical quote context.
   - Applies bulk discount rules.
4. **`SalesAgent`** (worker)
   - Validates stock, records sales transactions, and can produce financial summaries.
   - Estimates supplier delivery dates based on order size.

> Note: The evaluation runner in `project_starter.py` instantiates the worker agents and passes them into `OrchestrationAgent` via `managed_agents`, so the orchestrator delegates inventory checks, quote generation, and sales processing to distinct specialist agents.

---

## Tools (and the required helper functions they use)

All tools are defined with `@tool` and intentionally wrap the database helper functions from `project_starter.py`.

| Tool (agent-facing)                                        | Purpose                                        | Helper function(s) used                         |
| ---------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------- |
| `check_all_inventory(as_of_date)`                          | Snapshot of all stock + reorder flags          | `get_all_inventory` (+ reads `inventory` table) |
| `check_item_stock(item_name, as_of_date)`                  | Stock + unit price + reorder flag for one item | `get_stock_level` (+ reads `inventory` table)   |
| `search_quote_history_tool(search_terms, limit)`           | Retrieve similar historical quotes             | `search_quote_history`                          |
| `get_catalog_items()`                                      | Show full catalog with list prices             | (reads in‑memory `paper_supplies`)              |
| `process_sale(item_name, quantity, sale_price, sale_date)` | Record sale if stock is sufficient             | `get_stock_level`, `create_transaction`         |
| `estimate_supplier_delivery_date(order_date, quantity)`    | Estimate supplier lead time                    | `get_supplier_delivery_date`                    |
| `check_cash_balance(as_of_date)`                           | Cash on hand (sales – purchases)               | `get_cash_balance`                              |
| `generate_financial_report_tool(as_of_date)`               | Cash + inventory valuation + top sellers       | `generate_financial_report`                     |

Rubric coverage (required helper functions):

- `create_transaction` → used by `process_sale`
- `get_all_inventory` → used by `check_all_inventory`
- `get_stock_level` → used by `check_item_stock` and `process_sale`
- `get_supplier_delivery_date` → used by `estimate_supplier_delivery_date`
- `get_cash_balance` → used by `check_cash_balance` and `generate_financial_report`
- `generate_financial_report` → used by `generate_financial_report_tool`
- `search_quote_history` → used by `search_quote_history_tool`

---

## Pricing & quoting rules

The quoting logic is guided by the `QuotingAgent` instructions:

- Always verify availability first (`check_item_stock` / `check_all_inventory`).
- Use `get_catalog_items` for baseline unit prices.
- Use `search_quote_history_tool` to retrieve similar past quotes for context.
- Bulk discounts:
  - 5% discount for orders over $500
  - 10% discount for orders over $1000

Customer-facing outputs are expected to be **explainable** (what’s included, what discount applied) without exposing internal system details (e.g., raw tool traces or internal DB errors).

---

## Setup

### 1) Create and activate a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

Additional packages may be required depending on your environment (the code imports `numpy` and `smolagents`):

```powershell
pip install numpy smolagents
```

### 3) Configure environment variables

Create a `.env` file in the project root (or set environment variables) with:

```text
OPENAI_API_KEY=your_key_here
OPENAI_API_BASE_URL=https://api.openai.com/v1
```

Notes:

- `OPENAI_API_BASE_URL` can point to OpenAI or another compatible API base.
- The model is configured in `project_starter.py` via `OpenAIServerModel(...)`.

---

## Run the evaluation (generates `test_results.csv`)

Running the script will:

1. initialize the SQLite database (`munder_difflin.db`),
2. seed starting cash + inventory transactions,
3. iterate through every request in `quote_requests_sample.csv`,
4. write results to `test_results.csv`.

Command:

```powershell
python project_starter.py
```

Outputs:

- `munder_difflin.db` (created/overwritten during initialization)
- `test_results.csv` (evaluation output)

`test_results.csv` includes:

- `request_id`, `request_date`
- `cash_balance`, `inventory_value` after the request is processed
- `response` (customer-facing message from the orchestrator)

Evaluation expectations (per rubric):

- At least three requests should result in a **cash balance change** (sales processed).
- At least three quote requests should be **successfully fulfilled**.
- Not all requests should be fulfilled (e.g., **insufficient stock**), and the response should clearly state why.

---

## Workflow diagram

The workflow is captured in `workflow_diagram.md` as Mermaid diagrams:

- a **sequence diagram** for end-to-end request handling,
- a **flowchart** for orchestration decisions,
- tool → helper function mapping.

If your submission requires an image file, export the Mermaid diagram to PNG (e.g., using Mermaid Live Editor or a VS Code Mermaid extension).

---

## Submission checklist

Typical submission artifacts for this assignment:

- Workflow diagram (exported image)
- Single Python file: `project_starter.py`
- Evaluation output: `test_results.csv` (generated by running the script)
- Written report / reflection (usually submitted separately from this README)

---

## Data & database

### Seed data

- `quote_requests.csv` seeds the `quote_requests` table.
- `quotes.csv` seeds the `quotes` table and is used by `search_quote_history`.
- A sample subset of products is placed into the `inventory` table using `generate_sample_inventory(...)`.

### Database file

- SQLite DB file: `munder_difflin.db`
- Key tables:
  - `inventory` (reference table: items, unit price, minimum stock thresholds)
  - `transactions` (append-only log of `stock_orders` and `sales`)
  - `quote_requests`, `quotes` (historical context)

---

## Best-practice constraints (customer-facing output)

The agents are instructed to:

- provide the information directly relevant to the customer’s request (items, quantities, pricing, delivery expectations),
- include rationale for key outcomes (discounts applied; reasons an order cannot be fulfilled),
- avoid exposing sensitive internal details (exact internal margins, raw tool traces, stack traces).

---

## Troubleshooting

- **Missing package errors**: install missing deps with `pip install numpy smolagents`.
- **Auth / model errors**: verify `OPENAI_API_KEY` (and `OPENAI_API_BASE_URL` if applicable).
- **CSV not found**: run from the project root so `quote_requests_sample.csv` can be located.
