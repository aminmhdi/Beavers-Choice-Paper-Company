# Beaver's Choice Paper Company — Multi‑Agent Workflow Diagram

This diagram drafts the **agent responsibilities**, **orchestration logic**, and **tool/data flows** for the Beaver's Choice multi‑agent system, aligned to the helper functions and tool stubs in `project_starter.py`.

## Agents (max 5)

- **Orchestrator Agent**: customer-facing entry point; routes work to specialists; composes final response.
- **Inventory Agent**: answers stock questions; flags reorder needs based on `min_stock_level`.
- **Quoting Agent**: generates itemized quotes; consults inventory + catalog + historical quotes; applies bulk discounts.
- **Sales Agent**: confirms fulfillment feasibility; estimates delivery timelines; records sales transactions; can generate reports.

## Tools and their backing helper functions

- **check_all_inventory(as_of_date)** → `get_all_inventory(as_of_date)` (+ reads `inventory` table for `min_stock_level`, `unit_price`)
- **check_item_stock(item_name, as_of_date)** → `get_stock_level(item_name, as_of_date)` (+ reads `inventory` table for `min_stock_level`, `unit_price`)
- **search_quote_history_tool(search_terms, limit)** → `search_quote_history(search_terms, limit)`
- **estimate_supplier_delivery_date(order_date, quantity)** → `get_supplier_delivery_date(order_date, quantity)`
- **process_sale(item_name, quantity, sale_price, sale_date)** → `get_stock_level(...)` then `create_transaction(..., transaction_type="sales", ...)`
- **check_cash_balance(as_of_date)** → `get_cash_balance(as_of_date)`
- **generate_financial_report_tool(as_of_date)** → `generate_financial_report(as_of_date)` (internally uses `get_cash_balance` + `get_stock_level`)
- **(Catalog lookup)** get_catalog_items() → reads in‑memory `paper_supplies` list (no DB helper)

> Optional (often added in implementation): a **reorder tool** that records `transaction_type="stock_orders"` using `create_transaction(...)` when stock falls below `min_stock_level`.

---

## Sequence of operations (end‑to‑end)

```mermaid
---
id: addb3144-0db7-4c68-8934-98261275c948
---
sequenceDiagram
    autonumber

    actor Customer
    participant Orch as Orchestrator Agent
    participant Quote as Quoting Agent
    participant Inv as Inventory Agent
    participant Sales as Sales Agent
    participant DB as SQLite DB (munder_difflin.db)
    participant Supplier as Supplier (lead times)

    Customer->>Orch: Inquiry / quote request (includes request_date)

    Orch->>Quote: Draft quote + constraints

    %% Quote generation uses inventory, catalog, and quote history
    Quote->>Inv: Availability check (items, qty, as_of_date)
    Inv->>DB: get_stock_level() / get_all_inventory()
    Note over Inv,DB: Tools: check_item_stock, check_all_inventory

    Quote->>DB: search_quote_history()
    Note over Quote,DB: Tool: search_quote_history_tool

    Quote-->>Orch: Customer-facing quote (itemized + bulk discount rationale)
    Orch-->>Customer: Quote + expected delivery assumptions

    alt Customer accepts quote
        Customer->>Orch: Confirm order
        Orch->>Sales: Finalize sale (items, qty, sale_date)

        Sales->>DB: get_stock_level() (re-validate stock)
        Sales->>Supplier: get_supplier_delivery_date(order_date, quantity)
        Note over Sales,Supplier: Tool: estimate_supplier_delivery_date

        Sales->>DB: create_transaction(type="sales")
        Note over Sales,DB: Tool: process_sale

        Sales->>DB: get_cash_balance() / generate_financial_report()
        Note over Sales,DB: Tools: check_cash_balance, generate_financial_report_tool

        Sales-->>Orch: Confirmation (fulfilled lines + delivery date)
        Orch-->>Customer: Order confirmation / receipt

        opt Stock drops below minimum
            Inv->>DB: create_transaction(type="stock_orders")
            Note over Inv,DB: (optional) Reorder tool built on create_transaction
        end

    else Customer declines
        Orch-->>Customer: Close inquiry / offer alternatives
    end
```

---

## Orchestration logic (decision flow)

```mermaid
flowchart TD
    A[Customer request + request_date] --> B["Orchestrator Agent<br/>Parse intent: inquiry vs purchase<br/>Extract item_names + quantity"]

    B --> C["Quoting Agent<br/>Generate customer-facing quote"]

    C --> D{"Stock sufficient<br/>for requested items?"}

    D -->|Check| T1["Tool: check_item_stock / check_all_inventory<br/>Helper: get_stock_level / get_all_inventory<br/>+ inventory(min_stock_level, unit_price)"]
    T1 --> D

    C --> T2["Tool: get_catalog_items<br/>Source: in-memory paper_supplies"]
    T2 --> C

    C --> T3["Tool: search_quote_history_tool<br/>Helper: search_quote_history"]
    T3 --> C

    D -->|No| E["Orchestrator response:<br/>Cannot fulfill (or partial fulfill)<br/>Explain constraint + next steps"]
    D -->|Yes| F["Orchestrator sends quote:<br/>Items, unit price, subtotal<br/>Bulk discount, total"]

    F --> G{Customer approves?}
    G -->|No| H[End: inquiry closed]

    G -->|Yes| I["Sales Agent<br/>Finalize order"]

    I --> T4["Tool: estimate_supplier_delivery_date<br/>Helper: get_supplier_delivery_date"]
    T4 --> I

    I --> T5["Tool: process_sale<br/>Helpers: get_stock_level + create_transaction(type='sales')"]
    T5 --> I

    I --> T6["Tool: check_cash_balance / generate_financial_report_tool<br/>Helpers: get_cash_balance / generate_financial_report"]
    T6 --> I

    I --> J["Orchestrator sends confirmation:<br/>Fulfilled items + delivery date<br/>Receipt total"]

    J --> K{Below min_stock_level?}
    K -->|Yes| L["Inventory Agent recommends reorder<br/>(optional tool: create_transaction(type='stock_orders'))"]
    K -->|No| M[End]
```
