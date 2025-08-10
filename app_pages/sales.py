import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


def render(db):
    st.header("Manajemen Penjualan")

    if st.session_state.get("sale_added_success"):
        msg = st.session_state.get("sale_added_message", "Transaksi berhasil ditambahkan!")
        st.toast(msg)
        del st.session_state["sale_added_success"]
        if "sale_added_message" in st.session_state:
            del st.session_state["sale_added_message"]

    tab1, tab2 = st.tabs(["Data Penjualan", "Tambah Transaksi"])

    with tab1:
        sales_df = db.get_sales_data()

        if not sales_df.empty:
            col1, col2, col3 = st.columns(3)

            with col1:
                start_date = st.date_input("Dari Tanggal", value=datetime.now().date() - timedelta(days=30))
            with col2:
                end_date = st.date_input("Sampai Tanggal", value=datetime.now().date())
            with col3:
                product_filter = st.selectbox("Filter Produk", ["Semua"] + sales_df['nama_produk'].unique().tolist())

            filtered_df = sales_df.copy()
            filtered_df['tanggal'] = pd.to_datetime(filtered_df['tanggal'], errors='coerce', utc=True).dt.tz_localize(None)
            filtered_df = filtered_df[
                (filtered_df['tanggal'].dt.date >= start_date)
                & (filtered_df['tanggal'].dt.date <= end_date)
            ]

            if product_filter != "Semua":
                filtered_df = filtered_df[filtered_df['nama_produk'] == product_filter]

            display_df = filtered_df[['tanggal', 'nama_produk', 'varian', 'jumlah', 'harga_satuan', 'total_harga']].copy()

            display_df['tanggal'] = display_df['tanggal'].dt.strftime('%Y-%m-%d %H:%M')

            gb = GridOptionsBuilder.from_dataframe(display_df)

            gb.configure_default_column(
                resizable=True,
                filterable=True,
                sortable=True,
                editable=False,
                groupable=True,
                floatingFilter=True,
                enableRowGroup=True,
                enablePivot=True,
                enableValue=True,
            )

            gb.configure_column('tanggal', header_name='Tanggal', width=150)
            gb.configure_column('nama_produk', header_name='Produk', width=200)
            gb.configure_column('varian', header_name='Varian', width=150)
            gb.configure_column('jumlah', header_name='Jumlah', width=100, type=['numericColumn', 'numberColumnFilter'])
            gb.configure_column('harga_satuan', header_name='Harga Satuan', width=150, type=['numericColumn', 'numberColumnFilter'],
                               valueFormatter="'Rp ' + value.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.')")
            gb.configure_column('total_harga', header_name='Total', width=150, type=['numericColumn', 'numberColumnFilter'],
                               valueFormatter="'Rp ' + value.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.')")

            gb.configure_grid_options(
                domLayout='autoHeight',
                enableRangeSelection=True,
                rowSelection='single',
                pagination=True,
                paginationPageSize=10,
                defaultColDef={'filter': True, 'sortable': True, 'resizable': True},
            )

            grid_options = gb.build()

            try:
                AgGrid(
                    display_df,
                    gridOptions=grid_options,
                    data_return_mode=DataReturnMode.AS_INPUT,
                    update_mode=GridUpdateMode.MODEL_CHANGED,
                    fit_columns_on_grid_load=True,
                    theme='streamlit',
                    height=500,
                    width='100%',
                    enable_enterprise_modules=False,
                    reload_data=False,
                    allow_unsafe_jscode=True,
                )
            except Exception as e:
                st.error(f"Error displaying data: {str(e)}")
                st.dataframe(display_df, use_container_width=True)

            total_transactions = len(filtered_df)
            total_revenue = filtered_df['total_harga'].sum()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Transaksi", total_transactions)
            with col2:
                st.metric("Total Pendapatan", f"Rp {total_revenue:,.0f}")
        else:
            st.info("Belum ada data penjualan")

    with tab2:
        st.subheader("Tambah Transaksi Baru")

        products_df = db.get_products()

        if not products_df.empty:
            with st.form("add_sale_form"):
                col1, col2 = st.columns(2)

                with col1:
                    tanggal = st.date_input("Tanggal Transaksi", value=datetime.now().date())
                    product_id = st.selectbox(
                        "Pilih Produk",
                        options=products_df['id'].tolist(),
                        format_func=lambda x: f"{products_df[products_df['id']==x]['nama_produk'].iloc[0]} - {products_df[products_df['id']==x]['varian'].iloc[0]}",
                    )

                with col2:
                    jumlah = st.number_input("Jumlah", min_value=0.1, value=1.0, step=0.1)
                    selected_product = products_df[products_df['id'] == product_id].iloc[0]
                    harga_satuan = st.number_input("Harga Satuan", value=int(selected_product['harga']))

                total = jumlah * harga_satuan
                st.info(f"Total: Rp {total:,.0f}")

                submitted = st.form_submit_button("Tambah Transaksi")

                if submitted:
                    if db.add_sale(tanggal, product_id, jumlah, harga_satuan):
                        product_label = products_df[products_df['id']==product_id]['nama_produk'].iloc[0]
                        st.session_state["sale_added_success"] = True
                        st.session_state["sale_added_message"] = f"Transaksi '{product_label}' berhasil ditambahkan"
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan transaksi!")
        else:
            st.info("Belum ada data produk. Silakan tambah produk terlebih dahulu.")
