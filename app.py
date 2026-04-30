import streamlit as st
import mysql.connector
import pandas as pd

st.set_page_config(page_title="Panel E-commerce", layout="wide")

@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host="127.0.0.1", 
        user="root", 
        password="rootpassword", 
        database="projekt_gumulak_judka",
        ssl_disabled=True,
        autocommit=True
    )

try:
    conn = init_connection()
    if not conn.is_connected():
        conn.reconnect(attempts=3, delay=2)
    cursor = conn.cursor(dictionary=True)
except Exception as e:
    st.error(f"Błąd połączenia z bazą: {e}")
    st.stop()

st.title("Panel Zarządzania E-commerce")

tab_klienci, tab_magazyn, tab_koszyki, tab_zamowienia, tab_faktury, tab_akcje = st.tabs([
    "Klienci", "Magazyn", "Koszyki", "Zamówienia", "Faktury", "Akcje (Zarządzanie)"
])

# sekcja widokow przeznaczona tylko do odczytu i prezentacji danych

with tab_klienci:
    st.header("Lista klientów")
    st.markdown("Wykorzystuje tabelę `customers`")
    if st.button("Odśwież listę klientów"):
        cursor.execute("SELECT * FROM customers LIMIT 100")
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Brak klientów w bazie.")

with tab_magazyn:
    st.header("Stan Magazynowy")
    st.markdown("Wykorzystuje widok `v_inventory`")
    if st.button("Odśwież stan magazynu"):
        cursor.execute("SELECT * FROM v_inventory LIMIT 100")
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Brak danych w magazynie.")

with tab_koszyki:
    st.header("Podgląd Koszyków i Przedmiotów")
    st.markdown("Wykorzystuje tabele `cart` oraz `cart_item`")
    if st.button("Odśwież podgląd koszyków"):
        st.subheader("Tabela: cart")
        cursor.execute("SELECT * FROM cart ORDER BY updated_at DESC LIMIT 50")
        df_cart = pd.DataFrame(cursor.fetchall())
        if not df_cart.empty:
            st.dataframe(df_cart, use_container_width=True)
        else:
            st.info("Brak koszyków w bazie.")
            
        st.subheader("Tabela: cart_item")
        cursor.execute("SELECT * FROM cart_item ORDER BY cart_id DESC LIMIT 50")
        df_items = pd.DataFrame(cursor.fetchall())
        if not df_items.empty:
            st.dataframe(df_items, use_container_width=True)
        else:
            st.info("Brak przedmiotów w koszykach (cart_item).")

with tab_zamowienia:
    st.header("Lista Zamówień")
    st.markdown("Wykorzystuje widok `v_customer_orders`")
    if st.button("Odśwież listę zamówień"):
        cursor.execute("SELECT * FROM v_customer_orders LIMIT 100") 
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Brak zamówień w bazie.")

with tab_faktury:
    st.header("Wystawione Faktury")
    st.markdown("Wykorzystuje tabelę `invoices`")
    if st.button("Odśwież listę faktur"):
        cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 100")
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Brak faktur w bazie.")

# sekcja operacyjna do modyfikacji stanu bazy danych poprzez procedury

with tab_akcje:
    st.header("Panel Operacyjny")
    
    with st.expander("Zarejestruj nowego klienta"):
        st.markdown("Wykorzystuje procedurę `add_customer`")
        with st.form("add_customer_form"):
            fn = st.text_input("Imię")
            ln = st.text_input("Nazwisko")
            submit_cust = st.form_submit_button("Dodaj Klienta")
            if submit_cust:
                try:
                    cursor.callproc('add_customer', [fn, ln])
                    conn.commit()
                    st.success(f"Dodano klienta: {fn} {ln}")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Dodaj produkt do koszyka"):
        st.markdown("Wykorzystuje widok `v_product_details` oraz procedurę `add_product_to_cart`")
        with st.form("add_to_cart_form"):
            cursor.execute("SELECT * FROM v_product_details LIMIT 100")
            prods = cursor.fetchall()
            if prods:
                keys = list(prods[0].keys())
                col_name = next((k for k in keys if 'name' in k.lower()), keys[1] if len(keys) > 1 else keys[0])
                id_col = next((k for k in keys if 'id' in k.lower()), keys[0])
                
                prod_options = {f"{p[col_name]} (ID: {p[id_col]})": p[id_col] for p in prods}
                
                selected_prod_name = st.selectbox("Wybierz produkt", options=list(prod_options.keys()))
                qty = st.number_input("Ilość", min_value=1, step=1)
                c_id = st.number_input("ID Klienta", min_value=1, step=1)
                
                submit_cart = st.form_submit_button("Dodaj do koszyka")
                if submit_cart:
                    try:
                        cursor.callproc('add_product_to_cart', [prod_options[selected_prod_name], qty, c_id])
                        conn.commit()
                        st.success("Produkt dodany do koszyka.")
                    except Exception as e:
                        st.error(f"Błąd procedury: {e}")
            else:
                st.warning("Brak produktów w widoku v_product_details.")

    with st.expander("Dodaj dane dostawy (Shipping)"):
        st.markdown("Wykorzystuje procedurę `add_shipping_details`")
        with st.form("add_shipping_form"):
            s_c_id = st.number_input("ID Klienta (customer_id)", min_value=1, step=1, key="s_cid")
            s_prov_id = st.number_input("ID Przewoźnika (provider_id)", min_value=1, step=1, key="s_prov")
            s_title = st.text_input("Tytuł adresu (np. Dom, Praca)", key="s_tit")
            s_fname = st.text_input("Imię", key="s_fn")
            s_lname = st.text_input("Nazwisko", key="s_ln")
            s_addr1 = st.text_input("Adres 1 (Ulica)", key="s_a1")
            s_addr2 = st.text_input("Adres 2 (Nr domu/lokalu)", key="s_a2")
            s_email = st.text_input("Email", key="s_em")
            s_country = st.text_input("Kraj (kod dwuliterowy, np. PL)", max_chars=2, key="s_co")
            s_city = st.text_input("Miasto", key="s_ci")
            s_state = st.text_input("Województwo / Stan", key="s_st")
            s_zip = st.text_input("Kod pocztowy", key="s_zip")
            s_phone = st.text_input("Telefon", key="s_ph")
            
            submit_ship = st.form_submit_button("Zapisz dane dostawy")
            if submit_ship:
                try:
                    cursor.execute(
                        "CALL add_shipping_details(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, @out_id)",
                        (s_c_id, s_prov_id, s_title, s_fname, s_lname, s_addr1, s_addr2, s_email, s_country, s_city, s_state, s_zip, s_phone)
                    )
                    st.success(f"Dodano dane dostawy dla adresu '{s_title}'.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Dodaj dane rozliczeniowe (Billing)"):
        st.markdown("Wykorzystuje procedurę `add_billing_details`")
        with st.form("add_billing_form"):
            b_c_id = st.number_input("ID Klienta (customer_id)", min_value=1, step=1, key="b_cid")
            b_prov_id = st.number_input("ID Dostawcy Płatności (provider_id)", min_value=1, step=1, key="b_prov")
            b_title = st.text_input("Tytuł adresu", key="b_tit")
            b_fname = st.text_input("Imię", key="b_fn")
            b_lname = st.text_input("Nazwisko", key="b_ln")
            b_email = st.text_input("Email", key="b_em")
            b_phone = st.text_input("Telefon", key="b_ph")
            
            submit_bill = st.form_submit_button("Zapisz dane rozliczeniowe")
            if submit_bill:
                try:
                    cursor.execute(
                        "CALL add_billing_details(%s, %s, %s, %s, %s, %s, %s, @out_id)",
                        (b_c_id, b_prov_id, b_title, b_fname, b_lname, b_email, b_phone)
                    )
                    st.success(f"Dodano dane rozliczeniowe dla adresu '{b_title}'.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Złóż nowe zamówienie"):
        st.markdown("Wykorzystuje procedurę `add_order`")
        with st.form("add_order_form"):
            o_c_id = st.number_input("ID Klienta", min_value=1, step=1)
            o_bill_id = st.number_input("ID Dostawcy Płatności", min_value=1, step=1)
            o_ship_id = st.number_input("ID Przewoźnika", min_value=1, step=1)
            address_title = st.text_input("Tytuł adresu (address_title)")
            
            submit_order = st.form_submit_button("Złóż zamówienie")
            if submit_order:
                try:
                    cursor.callproc('add_order', [o_c_id, o_bill_id, o_ship_id, address_title])
                    conn.commit()
                    st.success(f"Zamówienie dla klienta {o_c_id} zostało złożone.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Opłać zamówienie"):
        st.markdown("Wykorzystuje procedurę `pay_order`")
        with st.form("pay_order_form"):
            order_id_to_pay = st.number_input("Wpisz ID Zamówienia", min_value=1, step=1)
            submit_pay = st.form_submit_button("Potwierdź płatność i wystaw fakturę")
            if submit_pay:
                try:
                    cursor.callproc('pay_order', [order_id_to_pay])
                    conn.commit()
                    st.success(f"Zamówienie {order_id_to_pay} zostało opłacone.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Przygotuj zamówienie do wysyłki"):
        st.markdown("Wykorzystuje procedurę `prepare_order_shipment`")
        with st.form("prepare_shipment_form"):
            order_id_to_prepare = st.number_input("Wpisz ID Zamówienia", min_value=1, step=1, key="prep_ord_id")
            submit_prepare = st.form_submit_button("Przygotuj do wysyłki")
            if submit_prepare:
                try:
                    cursor.callproc('prepare_order_shipment', [order_id_to_prepare])
                    conn.commit()
                    st.success(f"Zamówienie {order_id_to_prepare} przygotowane do wysyłki.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Wyślij zamówienie"):
        st.markdown("Wykorzystuje procedurę `ship_order`")
        with st.form("ship_order_form"):
            order_id_to_ship = st.number_input("Wpisz ID Zamówienia", min_value=1, step=1, key="ship_ord_id")
            submit_ship = st.form_submit_button("Zmień status na 'Wysłane'")
            if submit_ship:
                try:
                    cursor.callproc('ship_order', [order_id_to_ship])
                    conn.commit()
                    st.success(f"Zamówienie {order_id_to_ship} zostało wysłane.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Zwróć zamówienie"):
        st.markdown("Wykorzystuje procedurę `return_order`")
        with st.form("return_order_form"):
            order_id_to_return = st.number_input("Wpisz ID Zamówienia", min_value=1, step=1, key="ret_ord_id")
            submit_return = st.form_submit_button("Zwróć zamówienie")
            if submit_return:
                try:
                    cursor.callproc('return_order', [order_id_to_return])
                    conn.commit()
                    st.success(f"Zamówienie {order_id_to_return} zostało zwrócone.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Anuluj zamówienie"):
        st.markdown("Wykorzystuje procedurę `cancel_order`")
        with st.form("cancel_order_form"):
            order_id_to_cancel = st.number_input("Wpisz ID Zamówienia", min_value=1, step=1, key="canc_ord_id")
            submit_cancel = st.form_submit_button("Anuluj zamówienie")
            if submit_cancel:
                try:
                    cursor.callproc('cancel_order', [order_id_to_cancel])
                    conn.commit()
                    st.success(f"Zamówienie {order_id_to_cancel} zostało anulowane.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")