import streamlit as st
import pandas as pd
import plotly.express as px


def render(db):
    st.markdown(
        """
    <div class="main-header">
        <h1>Dashboard Penjualan Toko Material</h1>
        <p>Sistem Prediksi dan Manajemen Stok Material</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    products_df = db.get_products()
    sales_df = db.get_sales_data()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_products = len(products_df)
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>Total Produk</h3>
            <p class="metric-value">{total_products}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        total_sales = len(sales_df)
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>Total Transaksi</h3>
            <p class="metric-value">{total_sales}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>Produk Aktif</h3>
            <p class="metric-value">{total_products}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        if not sales_df.empty:
            total_revenue = sales_df["total_harga"].sum()
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>Total Pendapatan</h3>
                <p class="metric-value">Rp {total_revenue:,.0f}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
            <div class="metric-card">
                <h3>Total Pendapatan</h3>
                <p class="metric-value">Rp 0</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Tren Penjualan Bulanan")
        if not sales_df.empty:
            sales_df["tanggal"] = pd.to_datetime(sales_df["tanggal"])
            monthly_sales = sales_df.groupby(sales_df["tanggal"].dt.to_period("M"))["total_harga"].sum()

            fig = px.line(
                x=monthly_sales.index.astype(str),
                y=monthly_sales.values,
                title="Tren Pendapatan Bulanan",
            )
            fig.update_layout(xaxis_title="Bulan", yaxis_title="Pendapatan (Rp)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")

    with col2:
        st.subheader("Top 5 Produk Terlaris")
        if not sales_df.empty:
            top_products = (
                sales_df.groupby("nama_produk")["jumlah"].sum().sort_values(ascending=False).head(5)
            )

            fig = px.bar(
                x=top_products.values,
                y=top_products.index,
                orientation="h",
                title="Produk Terlaris",
            )
            fig.update_layout(xaxis_title="Jumlah Terjual", yaxis_title="Produk")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data penjualan")
