
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "ecommerce.db"


def seed_database():
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run create_db.py first.")

    customers = [
        (1, "Alice Martin", "alice@example.com", "2026-07-10"),
        (2, "Bob Smith", "bob@example.com", "2026-07-15"),
        (3, "Charlie Brown", "charlie@example.com", "2026-08-01"),
        (4, "Diana Wilson", "diana@example.com", "2026-08-12"),
        (5, "Emma Davis", "emma@example.com", "2026-09-02"),
        (6, "Frank Miller", "frank@example.com", "2026-09-18"),
    ]

    products = [
        (1, "Wireless Mouse", "Accessories", 2499),
        (2, "Mechanical Keyboard", "Accessories", 7999),
        (3, "USB-C Hub", "Accessories", 3999),
        (4, "27-inch Monitor", "Displays", 22999),
        (5, "Laptop Stand", "Accessories", 3499),
        (6, "Webcam", "Peripherals", 5999),
        (7, "Noise-Cancelling Headphones", "Audio", 12999),
        (8, "External SSD", "Storage", 8999),
    ]

    # We'll add the remaining seed data here.

    orders = [
        (1, 1, "2026-08-04", "completed"),
        (2, 2, "2026-08-15", "completed"),
        (3, 3, "2026-09-03", "completed"),
        (4, 1, "2026-09-18", "completed"),
        (5, 4, "2026-09-22", "completed"),
        (6, 5, "2026-10-02", "completed"),
        (7, 6, "2026-10-05", "completed"),
        (8, 2, "2026-10-09", "completed"),
        (9, 3, "2026-10-13", "completed"),
        (10, 4, "2026-10-16", "completed"),
        (11, 1, "2026-10-25", "completed"),
        (12, 5, "2026-10-28", "completed"),
        (13, 6, "2026-11-03", "completed"),
        (14, 2, "2026-11-09", "pending"),
        (15, 3, "2026-11-11", "cancelled"),
        (16, 4, "2026-11-12", "completed"),
    ]

    # Each key is an order ID.
    # Each value contains (product_id, quantity) pairs.
    order_products = {
        1: [(1, 1), (3, 1)],
        2: [(2, 1)],
        3: [(4, 1), (5, 1)],
        4: [(7, 1)],
        5: [(8, 1), (3, 2)],
        6: [(1, 2), (5, 1)],
        7: [(6, 1)],
        8: [(2, 1), (3, 1)],
        9: [(4, 1)],
        10: [(7, 1), (1, 1)],
        11: [(8, 1)],
        12: [(2, 1), (5, 1)],
        13: [(6, 2)],
        14: [(4, 1)],
        15: [(7, 1)],
        16: [(3, 2), (1, 1)],
    }


    # Map product IDs to prices.
    product_prices = {
        product_id: price_cents
        for product_id, name, category, price_cents in products
    }

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # Prevent duplicate seeding.
        existing = conn.execute(
            "SELECT COUNT(*) FROM customers"
        ).fetchone()[0]

        if existing > 0:
            print("Database already contains customers. Skipping seed.")
            return

        # Insert customers.
        conn.executemany(
            """
            INSERT INTO customers
                (customer_id, name, email, created_at)
            VALUES (?, ?, ?, ?)
            """,
            customers,
        )

        # Insert products.
        conn.executemany(
            """
            INSERT INTO products
                (product_id, name, category, price_cents)
            VALUES (?, ?, ?, ?)
            """,
            products,
        )

        # Insert orders.
        conn.executemany(
            """
            INSERT INTO orders
                (order_id, customer_id, order_date, status)
            VALUES (?, ?, ?, ?)
            """,
            orders,
        )

        # Build and insert order items.
        order_items = []

        for order_id, items in order_products.items():
            for product_id, quantity in items:
                order_items.append(
                    (
                        order_id,
                        product_id,
                        quantity,
                        product_prices[product_id],
                    )
                )

        conn.executemany(
            """
            INSERT INTO order_items
                (order_id, product_id, quantity, unit_price_cents)
            VALUES (?, ?, ?, ?)
            """,
            order_items,
        )

        # Create successful payments for completed orders.
        payments = []

        for order_id, customer_id, order_date, status in orders:
            if status != "completed":
                continue

            total_cents = sum(
                product_prices[product_id] * quantity
                for product_id, quantity in order_products[order_id]
            )

            payments.append(
                (order_id, order_id, total_cents, "paid", order_date)
            )

        conn.executemany(
            """
            INSERT INTO payments
                (payment_id, order_id, amount_cents, status, payment_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            payments,
        )

        # Two completed refunds and one pending refund.
        refunds = [
            (1, 8, 3999, "completed", "2026-10-15"),
            (2, 11, 2000, "completed", "2026-10-29"),
            (3, 13, 1500, "pending", "2026-11-06"),
        ]

        conn.executemany(
            """
            INSERT INTO refunds
                (refund_id, payment_id, amount_cents, status, refund_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            refunds,
        )

    print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()
