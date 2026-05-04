# Configuration
- DBMS: MySQL/MariaDB 11
- Engine: InnoDB

---

# Tables:
- addresses: customer saved addresses for autofilling payment and shipping details
- attributes: product attributes (size, color, etc.)
- billing_details: payment data
- cart: customer carts (one per order)
- cart_item: items in cart
- categories: product categories (using Nested Set)
- category_product: pivot table for products and categories
- customers: ecommerce shop customers
- invoice_lines: individual bought product information (tax, net price)
- invoices: customer invoices (available when order is paid)
- login_history: users and customers login timestamps (NOT FINISHED)
- orders: customer orders
- payment_providers: available payment methods/providers
- permissions: permissions for system users
- product_attribute: pivot table for products and attributes
- products: information about clothes (configurable & simple)
- role_permission: pivot table for roles and permissions
- role_user: pivot table for users and roles
- roles: grouped permissions assigned to users
- shipping_details: shipment data
- shipping_providers: shipping companies
- stock_events: stock level history logs (Event Sourcing)
- users: ecommerce shop workers/admins
- vendors: product manufacturers

---

# Views:
- v_categories_tree: hierarchical representation of categories (Nested Set)
- v_customer_orders: customer orders with aggregated info
- v_inventory: current stock levels based on stock_events
- v_order_details: detailed order view (products, quantities, prices)
- v_permission_IDs: helper view mapping permissions
- v_product_details: extended product info (attributes, categories, vendor)
- v_role_IDs: helper view mapping roles
- v_user_IDs: helper view mapping users

---

# Functions:
- calculate_cart_total_value: calculates total cart value (gross/net)
- check_billing_details: validates billing data
- check_sellable_product_quantity: checks if requested quantity is available
- check_shipping_details: validates shipping data
- generate_email: generates random email
- generate_random_date: generates random date in range
- generate_random_hashed_password: generates hashed password
- generate_random_ip: generates random IP address
- generate_random_number: generates random number in range
- generate_random_user_agent: generates random user agent string
- generate_tracking_url: generates shipment tracking URL
- generate_transaction_id: generates transaction ID for payments
- remove_diacritics: removes diacritics from text

---

# Procedures:
- add_billing_details: add billing details for customer without saved address
- add_customer: create new customer
- add_invoice_lines: add invoice line entries
- add_login_log: store login history for user/customer
- add_order: create new order with status='placed'
- add_product_to_cart: add or update product quantity in cart
- add_role_permission: assign permission to role
- add_role_user: assign role to user
- add_shipping_details: add shipping details
- add_user: create new user
- cancel_order: cancel order (if not shipped) and log stock event
- change_stock_level: update stock based on order events
- delete_product_from_cart: soft delete product from cart
- increase_quantity: increase product quantity in cart
- pay_order: process payment, generate invoice + lines, set status='paid'
- prepare_order_shipment: generate tracking + set status='ready_to_ship'
- return_order: handle returned order and update stock
- ship_order: set order status='shipped'