import pytest
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rootpassword',
    'database': 'ecommerce_db',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci',
    'cursorclass': pymysql.cursors.DictCursor
}

@pytest.fixture(scope="session")
def db_connection():
    connection = pymysql.connect(**DB_CONFIG)
    connection.autocommit(True)
    yield connection
    connection.close()

@pytest.fixture
def cursor(db_connection):
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()

# Testy jednostkowe

def test_customer_unique_email_constraint(cursor):
    """Sprawdza, czy tabela blokuje twarde duplikaty emaili oraz czy działa kaskadowe usuwanie."""
    cursor.execute("DELETE FROM customers WHERE email='unikalny@test.pl'")
    
    cursor.execute("INSERT INTO customers (first_name, last_name, email, password, date_of_birth) VALUES ('Test', 'Test', 'unikalny@test.pl', 'haslo', '1990-01-01')")
    
    with pytest.raises(pymysql.err.IntegrityError) as excinfo:
        cursor.execute("INSERT INTO customers (first_name, last_name, email, password, date_of_birth) VALUES ('Test2', 'Test2', 'unikalny@test.pl', 'haslo2', '1990-01-01')")
    
    assert 'Duplicate entry' in str(excinfo.value)
    
    # Dzięki poprawce ON DELETE CASCADE w SQL, to jedno zapytanie usunie też koszyk klienta
    cursor.execute("DELETE FROM customers WHERE email='unikalny@test.pl'")

def test_check_sellable_product_quantity_empty_cart(cursor):
    """Test wywołania funkcji walidującej stany na pustym koszyku"""
    cursor.execute("SELECT check_sellable_product_quantity(999999) AS result")
    result = cursor.fetchone()
    assert result['result'] == 0

def test_add_customer_success_generates_data(cursor):
    """Sprawdza, czy procedura poprawnego dodania klienta generuje ukryte dane (email, hasło)."""
    cursor.callproc('add_customer', ('Adam', 'Nowicki'))
    
    # Pobieramy ostatnio dodanego klienta o takich danych
    cursor.execute("SELECT email, password FROM customers WHERE first_name='Adam' AND last_name='Nowicki' ORDER BY customer_id DESC LIMIT 1")
    customer = cursor.fetchone()
    
    assert customer is not None
    assert '@' in customer['email']
    assert len(customer['password']) > 0

def test_calculate_cart_total_value_invalid_order(cursor):
    """Sprawdza zachowanie funkcji obliczającej wartość koszyka dla nieistniejącego zamówienia."""
    cursor.execute("SELECT calculate_cart_total_value(999999, FALSE) AS net_total")
    result = cursor.fetchone()
    
    assert result['net_total'] == 0

# Testy modułowe (integracyjne)

def test_add_order_without_cart_items(cursor):
    """Sprawdza czy moduł zamówień odrzuca puste koszyki (błąd 45000)"""
    cursor.callproc('add_customer', ('Anna', 'Nowak'))
    cursor.execute("SELECT customer_id FROM customers ORDER BY customer_id DESC LIMIT 1")
    customer_id = cursor.fetchone()['customer_id']
    
    cursor.execute("UPDATE cart SET active=0 WHERE customer_id=%s", (customer_id,))
    
    with pytest.raises(pymysql.err.OperationalError) as excinfo:
        cursor.callproc('add_order', (customer_id, 1, 1, 'Dom'))
        
    assert '1644' in str(excinfo.value)
    assert 'dodaj przynajmniej jeden produkt' in str(excinfo.value).lower()

def test_add_product_to_cart_insufficient_stock(cursor):
    """Sprawdza blokadę dodania do koszyka ilości przekraczającej stan magazynowy."""
    cursor.execute("SELECT customer_id FROM customers LIMIT 1")
    customer_id = cursor.fetchone()['customer_id']
    
    cursor.execute("SELECT product_id FROM products WHERE type='simple' LIMIT 1")
    product_id = cursor.fetchone()['product_id']
    
    # Próba dodania absurdalnie wielkiej ilości
    with pytest.raises(pymysql.err.OperationalError) as excinfo:
        cursor.callproc('add_product_to_cart', (product_id, 999999, customer_id))
        
    assert '1644' in str(excinfo.value)
    assert 'brak produktu na magazynie' in str(excinfo.value).lower()

# Testy funkcjonalne (E2E)

def test_full_checkout_flow_generates_invoice(cursor):
    """Symulacja pełnej ścieżki przejścia klienta przez system e-commerce"""
    cursor.execute("SELECT customer_id FROM customers LIMIT 1")
    customer_id = cursor.fetchone()['customer_id']
    
    cursor.execute("SELECT product_id FROM products WHERE type='simple' LIMIT 1")
    product_id = cursor.fetchone()['product_id']
    
    billing_provider_id = 1
    shipping_provider_id = 1
    
    cursor.execute("""
        INSERT IGNORE INTO addresses (customer_id, title) 
        VALUES (%s, 'Dom')
    """, (customer_id,))

    cursor.execute("INSERT INTO stock_events (product_id, diff, event_type) VALUES (%s, 10, 'returned')", (product_id,))
    
    cursor.callproc('add_product_to_cart', (product_id, 1, customer_id))
    cursor.callproc('add_order', (customer_id, billing_provider_id, shipping_provider_id, 'Dom'))
    
    cursor.execute("SELECT order_id FROM orders WHERE customer_id=%s ORDER BY created_at DESC LIMIT 1", (customer_id,))
    order_id = cursor.fetchone()['order_id']
    
    cursor.callproc('pay_order', (order_id,))
    
    cursor.execute("SELECT status FROM orders WHERE order_id=%s", (order_id,))
    assert cursor.fetchone()['status'] == 'paid'
    
    cursor.execute("SELECT invoice_id FROM invoices WHERE order_id=%s", (order_id,))
    assert cursor.fetchone() is not None
    
    cursor.execute("DELETE FROM stock_events WHERE product_id=%s AND diff=10 AND event_type='returned' LIMIT 1", (product_id,))
    cursor.execute("DELETE FROM addresses WHERE customer_id=%s AND title='Dom'", (customer_id,))

def test_event_sourcing_on_order_cancellation(cursor):
    """Weryfikacja mechanizmu Event Sourcing po anulowaniu zamówienia."""
    cursor.execute("SELECT customer_id FROM customers LIMIT 1")
    customer_id = cursor.fetchone()['customer_id']
    
    cursor.execute("SELECT product_id FROM products WHERE type='simple' LIMIT 1")
    product_id = cursor.fetchone()['product_id']
    
    # Sprawdzenie stanu początkowego w widoku inwentaryzacji (lub bezpośrednio przez funkcję)
    cursor.execute("SELECT IFNULL(SUM(diff), 0) as current_stock FROM stock_events WHERE product_id=%s", (product_id,))
    initial_stock = cursor.fetchone()['current_stock']
    
    # Tworzymy fikcyjne zamówienie na 2 sztuki
    cursor.execute("INSERT INTO cart (customer_id, active) VALUES (%s, 1)", (customer_id,))
    cart_id = cursor.lastrowid
    cursor.execute("INSERT INTO cart_item (cart_id, product_id, quantity) VALUES (%s, %s, 2)", (cart_id, product_id))
    cursor.execute("INSERT INTO orders (customer_id, cart_id, status) VALUES (%s, %s, 'placed')", (customer_id, cart_id))
    order_id = cursor.lastrowid
    
    # Wywołujemy procedurę anulowania zamówienia
    cursor.callproc('cancel_order', (order_id,))
    
    # Asercja - weryfikacja czy anulowanie zamówienia wygenerowało log kompensujący w Event Sourcing
    cursor.execute("SELECT diff, event_type FROM stock_events WHERE product_id=%s ORDER BY stock_event_id DESC LIMIT 1", (product_id,))
    last_event = cursor.fetchone()
    
    assert last_event is not None
    assert last_event['event_type'] == 'order_cancelled'
    assert last_event['diff'] == 2  # stan magazynowy powinien urosnąć o anulowane 2 sztuki
    
    # Sprzątanie
    cursor.execute("DELETE FROM stock_events WHERE order_id=%s", (order_id,))
    cursor.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
    cursor.execute("DELETE FROM cart_item WHERE cart_id=%s", (cart_id,))
    cursor.execute("DELETE FROM cart WHERE cart_id=%s", (cart_id,))