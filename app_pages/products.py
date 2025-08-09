import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


def render(db):
    st.header("Manajemen Produk")

    tab1, tab2 = st.tabs(["Daftar Produk", "Tambah Produk"])

    with tab1:
        products_df = db.get_products()

        if not products_df.empty:
            col1, col2 = st.columns([3, 1])
            with col1:
                search = st.text_input("Cari produk", placeholder="Nama produk...")
            with col2:
                if st.button("Refresh"):
                    st.rerun()

            if search:
                products_df = products_df[
                    products_df['nama_produk'].str.contains(search, case=False, na=False)
                    | products_df['varian'].str.contains(search, case=False, na=False)
                ]

            display_data = []
            for _, row in products_df.iterrows():
                try:
                    display_data.append({
                        'Nama Produk': str(row['nama_produk']) if pd.notna(row['nama_produk']) else '',
                        'Varian': str(row['varian']) if pd.notna(row['varian']) else '',
                        'Jenis': str(row['jenis']) if pd.notna(row['jenis']) else '',
                        'Harga (Rp)': f"{int(row['harga']):,}".replace(',', '.') if pd.notna(row['harga']) else '0'
                    })
                except (ValueError, TypeError):
                    continue

            if display_data:
                try:
                    display_df = pd.DataFrame(display_data)

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

                    gb.configure_column('Nama Produk', header_name='Nama Produk', width=200)
                    gb.configure_column('Varian', header_name='Varian', width=150)
                    gb.configure_column('Jenis', header_name='Jenis', width=120)
                    gb.configure_column(
                        'Harga (Rp)',
                        header_name='Harga (Rp)',
                        width=150,
                        type=['numericColumn', 'numberColumnFilter'],
                        valueFormatter="value.toLocaleString('id-ID', {style:'currency', currency:'IDR', maximumFractionDigits:0}).replace('IDR', 'Rp')",
                    )

                    try:
                        gb.configure_grid_options(
                            domLayout='autoHeight',
                            enableRangeSelection=True,
                            rowSelection='single',
                            pagination=True,
                            paginationPageSize=10,
                            suppressRowClickSelection=True,
                            suppressCellSelection=True,
                            suppressRowDeselection=True,
                            suppressColumnVirtualisation=True,
                        )
                    except Exception:
                        gb.configure_grid_options(domLayout='autoHeight', pagination=True, paginationPageSize=10)

                    grid_options = gb.build()

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
                    st.error(f"Error displaying table: {str(e)}")
                    st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("Tidak ada data produk yang tersedia.")
        else:
            st.info("Belum ada data produk. Silakan tambah produk baru atau import data Excel.")

    with tab2:
        st.subheader("Tambah Produk Baru")

        with st.form("add_product_form"):
            col1, col2 = st.columns(2)

            with col1:
                nama_produk = st.text_input("Nama Produk *")
                varian = st.text_input("Varian")
                jenis = st.text_input("Jenis *")

            with col2:
                harga = st.number_input("Harga *", min_value=0, value=0)

            submitted = st.form_submit_button("Tambah Produk")

            if submitted:
                if nama_produk and jenis and harga > 0:
                    if db.add_product(nama_produk, varian, jenis, harga):
                        st.success("Produk berhasil ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Gagal menambahkan produk!")
                else:
                    st.warning("Mohon lengkapi data yang wajib diisi.")
