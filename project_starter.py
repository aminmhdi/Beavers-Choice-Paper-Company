import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from smolagents import (
    ToolCallingAgent,
    OpenAIServerModel,
    tool,
)
from sqlalchemy import create_engine, Engine

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE lower(item_name) = lower(:item_name)
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11-100 units: 1 day
        - 101-1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0

def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }

def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


# Set up and load your env parameters and instantiate your model.
dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_base = os.getenv("OPENAI_API_BASE_URL")

# Initialize the model with the API key
model = OpenAIServerModel(
    model_id="gpt-4o-mini",
    api_base=openai_api_base,
    api_key=openai_api_key,
)


"""Set up tools for your agents to use, these should be methods that combine the database functions above
 and apply criteria to them to ensure that the flow of the system is correct."""


# Tools for inventory agent
@tool
def check_all_inventory(as_of_date: str) -> str:
    """
    Check the full inventory showing all items with their current stock levels and and reorder status.
    
    Args:
        as_of_date (str): The date for which to check inventory, in ISO format (YYYY-MM-DD).

    Returns:
        str: A formatted string listing each item, its stock level, and whether it needs reordering.
    """    
    inventory = get_all_inventory(as_of_date)
    if not inventory:
        return f"No inventory available in {as_of_date}."
    
    # Fetch min stock levels from the inventory table
    inventory_df = pd.read_sql("SELECT item_name, min_stock_level, unit_price FROM inventory", db_engine)
    min_stock_dict = dict(zip(inventory_df["item_name"], inventory_df["min_stock_level"]))
    price_dict = dict(zip(inventory_df["item_name"], inventory_df["unit_price"]))

    # Build the inventory report
    report_lines = []
    for item_name, stock in inventory.items():
        min_stock = min_stock_dict.get(item_name, 0)
        unit_price = price_dict.get(item_name, 0.0)
        reorder_status = "REORDER NEEDED" if stock <= min_stock else "Stock sufficient"
        report_lines.append(f"{item_name}: {stock} units (Unit Price: ${unit_price:.2f}) - {reorder_status}")

    return "Current Inventory:\n" + "\n".join(report_lines)


@tool
def check_item_stock(item_name: str, as_of_date: str) -> str:
    """
    Check the stock level of a specific item as of a given date, along with its reorder status.

    Args:
        item_name (str): The name of the item to check.
        as_of_date (str): The date for which to check stock, in ISO format (YYYY-MM-DD).

    Returns:
        str: A formatted string indicating the current stock level and whether it needs reordering.
    """
    
    stock_info = get_stock_level(item_name, as_of_date)
    if stock_info.empty:
        return f"No stock information found for '{item_name}' as of {as_of_date}."

    current_stock = int(stock_info["current_stock"].iloc[0])

    # Fetch min stock level and unit price from inventory table
    inventory_df = pd.read_sql(
        """
        SELECT 
            item_name, min_stock_level, unit_price 
        FROM 
            inventory
        WHERE 
            lower(item_name) = lower(:item_name)""", 
            db_engine, 
            params={"item_name": item_name}
        )
    
    if inventory_df.empty:
        return f"Item '{item_name}' not found in inventory records."

    min_stock = int(inventory_df["min_stock_level"].iloc[0])
    unit_price = float(inventory_df["unit_price"].iloc[0])
    
    reorder_status = "REORDER NEEDED" if current_stock <= min_stock else "Stock sufficient"
    
    return f"{item_name}: {current_stock} units (Unit Price: ${unit_price:.2f}) - {reorder_status}"


# Tools for quoting agent
@tool
def search_quote_history_tool(search_terms: List[str], limit: int = 5) -> str:
    """
    Search the quote history for past quotes that match the provided search terms and return a formatted string of results.

    Args:
        search_terms (List[str]): Keywords to search for in past quotes. Typically a list of strings,
            but comma-separated string input is also accepted.
        limit (int, optional): The maximum number of matching quotes to return. Default is 5.

    Returns:
        str: A formatted string listing the matching quotes with their details.
    """

    if isinstance(search_terms, str):
        normalized_terms = [term.strip() for term in search_terms.split(",") if term.strip()]
    elif isinstance(search_terms, list):
        normalized_terms = [str(term).strip() for term in search_terms if str(term).strip()]
    else:
        return "No valid search terms provided. Provide a comma-separated string or a list of strings."

    if not normalized_terms:
        return "No valid search terms provided. Please enter one or more keywords separated by commas."
    
    matching_quotes = search_quote_history(normalized_terms, limit)

    if not matching_quotes:
        return f"No quotes found matching the search terms: {', '.join(normalized_terms)}."
    
    result_lines = [f"Found {len(matching_quotes)} matching quotes:"]
    for quote in matching_quotes:
        result_lines.append(
            f"- Request: {quote['original_request']}\n"
            f"  Quote Explanation: {quote['quote_explanation']}\n"
            f"  Total Amount: ${quote['total_amount']:.2f}\n"
            f"  Job Type: {quote['job_type']}, Order Size: {quote['order_size']}, Event Type: {quote['event_type']}\n"
            f"  Order Date: {quote['order_date']}"
        )
    
    return "\n".join(result_lines)


# Tools for getting catalog information for quoting and ordering agents
@tool
def get_catalog_items() -> str:
    """
    Retrieve a list of all available items in the inventory catalog, including their categories and unit prices.

    Returns:
        str: A formatted string listing each item, its category, and unit price.
    """

    catalog_lines = ["Available Catalog Items:"]
    for item in paper_supplies:
        catalog_lines.append(
            f"- {item['item_name']} (Category: {item['category']}, Unit Price: ${item['unit_price']:.2f})"
        )
    
    return "\n".join(catalog_lines)


# Tools for sales agent
@tool
def process_sale(item_name: str, quantity: int, sale_price: float, sale_date: str) -> str:
    """
    Process a sale by recording it in the transactions table and updating inventory accordingly.

    Args:
        item_name (str): The name of the item being sold.
        quantity (int): The number of units sold.
        sale_price (float): The total price for the sale.
        sale_date (str): The date of the sale in ISO format (YYYY-MM-DD).

    Returns:
        str: A confirmation message indicating the sale was processed successfully, or an error message if it failed.
    """
    stock_info = get_stock_level(item_name, sale_date)

    if stock_info.empty:
        return f"Error: Item '{item_name}' not found in inventory."
    
    current_stock = int(stock_info["current_stock"].iloc[0])
    if quantity > current_stock:
        return f"Error: Insufficient stock for '{item_name}'. Current stock: {current_stock} units, requested: {quantity} units."
    
    total_sale_value = quantity * sale_price

    

    try:
        # Create a sales transaction
        transaction_id = create_transaction(
            item_name=item_name,
            transaction_type="sales",
            quantity=quantity,
            price=sale_price,
            date=sale_date
        )
        return (
            f"Sale processed successfully.\n"
            f"Transaction ID: {transaction_id}\n"
            f"Total Sale Value: ${total_sale_value:.2f}\n"
            f"Remaining Stock for '{item_name}': {current_stock - quantity} units.\n"
        )
    except Exception as e:
        return f"Error processing sale: {e}"


@tool
def estimate_supplier_delivery_date(order_date: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the order date and quantity.

    Args:
        order_date (str): The date of the order in ISO format (YYYY-MM-DD).
        quantity (int): The number of units being ordered.

    Returns:
        str: The estimated delivery date in ISO format (YYYY-MM-DD).
    """
    delivery_date = get_supplier_delivery_date(order_date, quantity)
    return f"Estimated delivery date for an order of {quantity} units placed on {order_date} is: {delivery_date}."


@tool
def check_cash_balance(as_of_date: str) -> str:
    """
    Check the current cash balance as of a specific date.

    Args:
        as_of_date (str): The date for which to check the cash balance, in ISO format (YYYY-MM-DD).
    
    Returns:
        str: A formatted string indicating the current cash balance as of the given date.
    """
    cash_balance = get_cash_balance(as_of_date)
    return f"Current cash balance as of {as_of_date}: ${cash_balance:.2f}"

@tool
def generate_financial_report_tool(as_of_date: str) -> str:
    """
    Generate a comprehensive financial report as of a specific date, including cash balance, inventory valuation, and top-selling products.

    Args:
        as_of_date (str): The date for which to generate the report, in ISO format (YYYY-MM-DD).

    Returns:
        str: A formatted string containing the financial report details.
    """
    report = generate_financial_report(as_of_date)
    
    report_lines = [
        f"Financial Report as of {report['as_of_date']}:",
        f"Cash Balance: ${report['cash_balance']:.2f}",
        f"Inventory Value: ${report['inventory_value']:.2f}",
        f"Total Assets: ${report['total_assets']:.2f}",
        "Inventory Summary:"
    ]
    
    for item in report["inventory_summary"]:
        report_lines.append(
            f"- {item['item_name']}: {item['stock']} units (Unit Price: ${item['unit_price']:.2f}, Value: ${item['value']:.2f})"
        )
    
    report_lines.append("Top Selling Products:")
    for product in report["top_selling_products"]:
        report_lines.append(
            f"- {product['item_name']}: {product['total_units']} units sold, Total Revenue: ${product['total_revenue']:.2f}"
        )
    
    return "\n".join(report_lines)


# Set up your agents and create an orchestration agent that will manage them.

# Inventory Agent: check stock levels, monitor inventory, and determine when to reorder supplies.
class InventoryAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[check_all_inventory, check_item_stock],
            model=model,
            name="inventory_agent",
            description=(
                "Responsible for monitoring inventory levels, checking stock for specific items, and determining when to reorder supplies. "
                "Uses the 'check_all_inventory' tool to get a full snapshot of inventory and the 'check_item_stock' tool for specific item inquiries."
            ),
            max_steps=3
)

# Quoting Agent: generate quotes for customer requests based on inventory and past quote history.
class QuotingAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[search_quote_history_tool, get_catalog_items],
            model=model,
            name="quoting_agent",
            description=(
                "Responsible for generating quotes for customer requests based on inventory levels and past quote history. "
                "Uses the 'search_quote_history_tool' to find past quotes, 'get_catalog_items' to retrieve catalog information, "
                "and relies on the orchestration agent to provide availability information from the inventory agent."
            ),
            instructions=(
                "You are a quoting agent for Beaver's Choice Paper Company\n"
                "When given a customer request: \n"
                "1. Assume the orchestration agent provides an availability summary (from the inventory agent).\n"
                "2. Look up catalog information using the get_catalog_items tool.\n"
                "3. Search quote history for similar requests using search_quote_history_tool to inform your quoting decisions.\n"
                "4. Apply discounts based on order size and customer history:\n"
                "   - 5% discount for orders over $500\n"
                "   - 10% discount for orders over $1000\n"
                "5. Generate a clear and concise quote that includes:\n"
                "   - Item, quantity, and unit price for each requested item\n"
                "   - Subtotal, applied discounts, and total amount\n"
                "6. If items are out of stock, state it cannot be fulfilled\n"
                "7. Never reveal internal tool usage or inventory details in the quote explanation. "
                "   The quote should be customer-facing and focused on the request and pricing."
            ),
            max_steps=5
        )


# Sales Agent: handle sales transactions, update inventory, and manage cash flow.
class SalesAgent(ToolCallingAgent):
    def __init__(self, model):
        super().__init__(
            tools=[process_sale, check_cash_balance, generate_financial_report_tool, estimate_supplier_delivery_date],
            model=model,
            name="sales_agent",
            description=(
                "Responsible for processing sales transactions, updating inventory, and managing cash flow. "
                "Uses the 'process_sale' tool to record sales, 'check_cash_balance' to monitor cash levels, "
                "'generate_financial_report_tool' to create financial reports, 'estimate_supplier_delivery_date' to predict delivery times, "
                "and relies on the orchestration agent to provide availability context from the inventory agent when needed."
            ),
            instructions=(
                "You are a sales agent for Beaver's Choice Paper Company\n"
                "When processing a sale:\n"
                "1. If the orchestration agent provides an availability summary, use it to guide what you attempt to sell.\n"
                "2. Use process_sale to record each in-stock line-item transaction and update inventory.\n"
                "3. After processing sales, check the updated cash balance using check_cash_balance.\n"
                "4. Generate a financial report using generate_financial_report_tool to assess the impact of\n"
                "   the sale on overall finances.\n"
                "5. If the sale depletes stock below minimum levels, use estimate_supplier_delivery_date\n"
                "   to inform the customer of expected restock times.\n"
                "6. Always provide clear and informative responses to the customer regarding their purchase and any relevant\n"
                "   inventory or financial information, without revealing internal tool usage.\n"
                "7. Never reveal internal tool usage or inventory details in customer communications."
            ),
            max_steps=15
        )

# Orchestration Agent: manage the flow of information between the inventory, quoting, and sales agents to handle customer requests end-to-end.
class OrchestrationAgent(ToolCallingAgent):
    def __init__(self, model, managed_agents=None):
        super().__init__(
            tools=[],
            model=model,
            name="orchestration_agent",
            description=(
                "Responsible for managing the flow of information between the inventory, quoting, and sales agents to handle customer requests end-to-end. "
                "Coordinates the use of all tools to ensure a seamless customer experience from inquiry to sale."
            ),
            instructions=(
                "You are the orchestration agent for Beaver's Choice Paper Company\n"
                "When given a customer request, you will:\n\n"
                
                "1. Understand: Parse the customer request to identify the items, quantities, and any specific requirements.\n"
                "2. Delegate Inventory: Call the managed agent 'inventory_agent' to check stock availability as of the request date.\n"
                "   - Call it as a tool with a JSON payload containing at least a 'task' string.\n"
                "3. Delegate Quoting: Call the managed agent 'quoting_agent' with the customer request + the inventory availability summary.\n"
                "4. Delegate Sales: If the request should be fulfilled now (default: yes for purchase-like requests), call the managed agent 'sales_agent' with the request date + the quote details and ask it to process the sale(s).\n"
                "5. Respond: Provide the customer with a clear response that includes the quote and any relevant information about stock availability and delivery times.\n" \
                "   - Itemized quote (quantity, unit price, discount, total price)\n"
                "   - Which items are fulfilled with expected delivery times\n"
                "   - Which items cannot be fulfilled and the reasons why\n"
                "   - Grand total for the order\n"
                
                "Rules:\n"
                "- Map customer request to exact inventory items and quantities. \n"
                "  Examples: 'heavyweight paper' -> 'Heavyweight Paper', '500 sheets of cardstock' -> 'Cardstock' with quantity 500\n" \
                "  'Need 200 sheets of glossy paper' -> 'Glossy Paper' with quantity 200\n" \
                "  'Looking for 100 sheets of recycled paper' -> 'Recycled Paper' with quantity 100\n" \
                "  'Construction paper for a school project, need 300 sheets' -> 'Construction Paper' with quantity 300\n" \
                "- Always delegate inventory checks to the inventory_agent before quoting.\n" \
                "- Always delegate quote generation to the quoting_agent.\n" \
                "- Always delegate sale processing to the sales_agent (do not call sales/inventory tools directly).\n" \
                "- Be professional and clear in all customer communications, providing detailed information about the quote and order status without revealing internal processes or tool usage. \n" \
                "- Never reveal internal tool usage or inventory details in the quote explanation. The quote should be customer-facing and focused on the request and pricing. \n"
                "- Provide clear and informative responses to the customer regarding their inquiry, including any relevant inventory or financial information, without revealing internal tool usage or internal processes."
            ),
            managed_agents=managed_agents,
            max_steps=20
        )

# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    # INITIALIZE AGENTS

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print("\n" + "="*30)
        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")
        print(f"Customer Request: {row['request']}")
        print("\n" + "="*30)

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"
        inventory_agent = InventoryAgent(model)
        quoting_agent = QuotingAgent(model)
        sales_agent = SalesAgent(model)

        orchestration_agent = OrchestrationAgent(
            model,
            managed_agents=[inventory_agent, quoting_agent, sales_agent],
        )

        try:
            response = orchestration_agent.run(request_with_date)
        except Exception as e:
            response = f"Error processing request: {e}"
            print(f"Error during agent execution: {e}")

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
