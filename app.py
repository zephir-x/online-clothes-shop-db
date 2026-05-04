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

tab_klienci, tab_magazyn, tab_koszyki, tab_zamowienia, tab_faktury, tab_logi, tab_akcje, tab_admin = st.tabs([
    "Klienci", "Magazyn", "Koszyki", "Zamówienia", "Faktury", "Logi Magazynowe", "Akcje (Zarządzanie)", "Administracja"
])

# sekcja widokow przeznaczona tylko do odczytu danych dla procesow logistycznych i sklepu

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
            
    st.header("Drzewo Kategorii Produkcyjnych")
    st.markdown("Wykorzystuje widok `v_categories_tree`")
    if st.button("Pokaż strukturę kategorii"):
        cursor.execute("SELECT * FROM v_categories_tree LIMIT 100")
        df_cat = pd.DataFrame(cursor.fetchall())
        if not df_cat.empty:
            st.dataframe(df_cat, use_container_width=True)
        else:
            st.info("Brak danych o kategoriach.")

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
        cursor.execute("SELECT * FROM v_customer_orders ORDER BY orderID DESC LIMIT 100") 
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Brak zamówień w bazie.")

    st.header("Szczegóły Zamówienia")
    st.markdown("Wykorzystuje widok `v_order_details`")
    col1, col2 = st.columns([1, 4])
    with col1:
        order_id_search = st.number_input("Wpisz ID zamówienia", min_value=1, step=1, key="search_ord_id")
    with col2:
        st.write("") 
        st.write("")
        if st.button("Pokaż zawartość"):
            cursor.execute("SELECT * FROM v_order_details WHERE orderID = %s", (order_id_search,))
            df_details = pd.DataFrame(cursor.fetchall())
            if not df_details.empty:
                st.dataframe(df_details, use_container_width=True)
            else:
                st.warning(f"Brak szczegółów dla zamówienia o ID {order_id_search}.")

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

with tab_logi:
    st.header("Dziennik Zdarzeń Magazynowych (Event Sourcing)")
    st.markdown("Wykorzystuje tabelę `stock_events`")
    if st.button("Odśwież logi magazynowe"):
        cursor.execute("SELECT * FROM stock_events ORDER BY created_at DESC LIMIT 100")
        df_events = pd.DataFrame(cursor.fetchall())
        if not df_events.empty:
            st.dataframe(df_events, use_container_width=True)
        else:
            st.info("Brak zdarzeń magazynowych.")

# sekcja operacyjna sklepu e-commerce

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

    with st.expander("Usuń produkt z koszyka"):
        st.markdown("Wykorzystuje widok `v_product_details` oraz procedurę `delete_product_from_cart`")
        with st.form("delete_from_cart_form"):
            cursor.execute("SELECT * FROM v_product_details LIMIT 100")
            prods = cursor.fetchall()
            if prods:
                keys = list(prods[0].keys())
                col_name = next((k for k in keys if 'name' in k.lower()), keys[1] if len(keys) > 1 else keys[0])
                id_col = next((k for k in keys if 'id' in k.lower()), keys[0])
                
                prod_options = {f"{p[col_name]} (ID: {p[id_col]})": p[id_col] for p in prods}
                
                selected_prod_name_del = st.selectbox("Wybierz produkt do usunięcia", options=list(prod_options.keys()), key="del_prod_sel")
                del_c_id = st.number_input("ID Klienta", min_value=1, step=1, key="del_c_id")
                
                submit_del_cart = st.form_submit_button("Usuń z koszyka")
                if submit_del_cart:
                    try:
                        cursor.callproc('delete_product_from_cart', [del_c_id, prod_options[selected_prod_name_del]])
                        conn.commit()
                        st.success("Produkt został usunięty z koszyka.")
                    except Exception as e:
                        st.error(f"Błąd procedury: {e}")
            else:
                st.warning("Brak produktów.")

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

    with st.expander("Zwiększ stan magazynowy (Dostawa)"):
        st.markdown("Wykorzystuje widok `v_product_details` oraz procedurę `increase_quantity`")
        with st.form("increase_quantity_form"):
            cursor.execute("SELECT * FROM v_product_details LIMIT 100")
            prods_stock = cursor.fetchall()
            if prods_stock:
                keys = list(prods_stock[0].keys())
                col_name = next((k for k in keys if 'name' in k.lower()), keys[1] if len(keys) > 1 else keys[0])
                id_col = next((k for k in keys if 'id' in k.lower()), keys[0])
                
                prod_options_stock = {f"{p[col_name]} (ID: {p[id_col]})": p[id_col] for p in prods_stock}
                
                selected_prod_stock = st.selectbox("Wybierz produkt", options=list(prod_options_stock.keys()), key="inc_prod_sel")
                inc_qty = st.number_input("Ilość dostarczona na magazyn", min_value=1, step=1, key="inc_qty")
                
                submit_inc_stock = st.form_submit_button("Zarejestruj dostawę")
                if submit_inc_stock:
                    try:
                        cursor.callproc('increase_quantity', [prod_options_stock[selected_prod_stock], inc_qty])
                        conn.commit()
                        st.success("Wysłano żądanie zwiększenia stanu magazynowego.")
                    except Exception as e:
                        st.error(f"Błąd procedury: {e}")
            else:
                st.warning("Brak produktów w widoku v_product_details.")

# sekcja panelu administracyjnego do zarzadzania uzytkownikami, rolami i bezpieczenstwem

with tab_admin:
    st.header("Panel Administratora")
    
    st.subheader("Użytkownicy (Pracownicy)")
    st.markdown("Wykorzystuje tabelę `users`")
    if st.button("Odśwież listę pracowników"):
        cursor.execute("SELECT * FROM users LIMIT 100")
        df_users = pd.DataFrame(cursor.fetchall())
        if not df_users.empty:
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("Brak pracowników w bazie.")

    st.subheader("Historia logowań")
    st.markdown("Wykorzystuje tabelę `login_history`")
    if st.button("Odśwież logowania"):
        cursor.execute("SELECT * FROM login_history ORDER BY created_at DESC LIMIT 100")
        df_logins = pd.DataFrame(cursor.fetchall())
        if not df_logins.empty:
            st.dataframe(df_logins, use_container_width=True)
        else:
            st.info("Brak logowań w bazie.")
            
    st.divider()

    with st.expander("Dodaj nowego pracownika"):
        st.markdown("Wykorzystuje procedurę `add_user`")
        with st.form("add_user_form"):
            u_fname = st.text_input("Imię")
            u_lname = st.text_input("Nazwisko")
            
            submit_user = st.form_submit_button("Zarejestruj pracownika")
            if submit_user:
                try:
                    cursor.callproc('add_user', [u_fname, u_lname])
                    conn.commit()
                    st.success("Dodano pracownika. Hasło oraz email wygenerowano automatycznie.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")

    with st.expander("Przypisz rolę do pracownika"):
        st.markdown("Wykorzystuje widoki `v_user_IDs`, `v_role_IDs` oraz procedurę `add_role_user`")
        with st.form("add_role_user_form"):
            cursor.execute("SELECT * FROM v_user_IDs")
            v_users = cursor.fetchall()
            cursor.execute("SELECT * FROM v_role_IDs")
            v_roles = cursor.fetchall()
            
            if v_users and v_roles:
                u_keys = list(v_users[0].keys())
                u_id_col = next((k for k in u_keys if 'id' in k.lower()), u_keys[0])
                u_name_col = next((k for k in u_keys if 'name' in k.lower()), u_keys[1] if len(u_keys) > 1 else u_keys[0])
                user_options = {f"{u[u_name_col]} (ID: {u[u_id_col]})": u[u_id_col] for u in v_users}
                
                r_keys = list(v_roles[0].keys())
                r_id_col = next((k for k in r_keys if 'id' in k.lower()), r_keys[0])
                r_name_col = next((k for k in r_keys if 'name' in k.lower()), r_keys[1] if len(r_keys) > 1 else r_keys[0])
                role_options = {f"{r[r_name_col]} (ID: {r[r_id_col]})": r[r_id_col] for r in v_roles}
                
                sel_user = st.selectbox("Wybierz pracownika", options=list(user_options.keys()))
                sel_role = st.selectbox("Wybierz rolę", options=list(role_options.keys()))
                
                submit_role_user = st.form_submit_button("Zaktualizuj rolę")
                if submit_role_user:
                    try:
                        cursor.callproc('add_role_user', [user_options[sel_user], role_options[sel_role]])
                        conn.commit()
                        st.success("Procedura wykonana.")
                    except Exception as e:
                        st.error(f"Błąd procedury: {e}")
            else:
                st.warning("Brak danych do załadowania formularza. Upewnij się, że widoki zwracają rekordy.")

    with st.expander("Przypisz uprawnienie do roli"):
        st.markdown("Wykorzystuje widoki `v_role_IDs`, `v_permission_IDs` oraz procedurę `add_role_permission`")
        with st.form("add_role_perm_form"):
            cursor.execute("SELECT * FROM v_role_IDs")
            v_roles2 = cursor.fetchall()
            cursor.execute("SELECT * FROM v_permission_IDs")
            v_perms = cursor.fetchall()
            
            if v_roles2 and v_perms:
                r2_keys = list(v_roles2[0].keys())
                r2_id_col = next((k for k in r2_keys if 'id' in k.lower()), r2_keys[0])
                r2_name_col = next((k for k in r2_keys if 'name' in k.lower()), r2_keys[1] if len(r2_keys) > 1 else r2_keys[0])
                role2_options = {f"{r[r2_name_col]} (ID: {r[r2_id_col]})": r[r2_id_col] for r in v_roles2}
                
                p_keys = list(v_perms[0].keys())
                p_id_col = next((k for k in p_keys if 'id' in k.lower()), p_keys[0])
                p_name_col = next((k for k in p_keys if 'name' in k.lower()), p_keys[1] if len(p_keys) > 1 else p_keys[0])
                perm_options = {f"{p[p_name_col]} (ID: {p[p_id_col]})": p[p_id_col] for p in v_perms}
                
                sel_role2 = st.selectbox("Wybierz rolę", options=list(role2_options.keys()), key="sel_r2")
                sel_perm = st.selectbox("Wybierz uprawnienie", options=list(perm_options.keys()))
                
                submit_role_perm = st.form_submit_button("Przypisz uprawnienie")
                if submit_role_perm:
                    try:
                        cursor.callproc('add_role_permission', [role2_options[sel_role2], perm_options[sel_perm]])
                        conn.commit()
                        st.success("Uprawnienie przypisane.")
                    except Exception as e:
                        st.error(f"Błąd procedury: {e}")
            else:
                st.warning("Brak danych do załadowania formularza.")

    with st.expander("Rejestruj logowanie (Symulacja zdarzenia)"):
        st.markdown("Wykorzystuje procedurę `add_login_log`")
        with st.form("add_login_log_form"):
            log_type = st.selectbox("Typ logującego", options=["user", "customer"])
            log_id = st.number_input("ID konta (użytkownika lub klienta)", min_value=1, step=1)
            log_action = st.selectbox("Wykonywana akcja", options=["add_to_cart", "add_order"])
            
            submit_log = st.form_submit_button("Rejestruj")
            if submit_log:
                try:
                    cursor.callproc('add_login_log', [log_type, log_id, log_action])
                    conn.commit()
                    st.success("Logowanie zapisane. Sprawdź tabelę login_history.")
                except Exception as e:
                    st.error(f"Błąd procedury: {e}")