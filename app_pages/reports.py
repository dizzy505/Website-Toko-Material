import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.express as px


def render(db):
    st.header("Laporan")

    tab_sales, tab_pred, tab_users, tab_abc = st.tabs([
        "Laporan Penjualan",
        "Laporan Prediksi",
        "Laporan Data User",
        "Laporan Kinerja Produk"
    ])

    with tab_sales:
        st.subheader("Laporan Penjualan")
        sales_df = db.get_sales_data()

        if not sales_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Dari Tanggal", value=datetime.now().date() - timedelta(days=30)
                )
            with col2:
                end_date = st.date_input("Sampai Tanggal", value=datetime.now().date())

            filtered_df = sales_df.copy()
            filtered_df["tanggal"] = pd.to_datetime(filtered_df["tanggal"], errors="coerce")
            filtered_df = filtered_df.dropna(subset=["tanggal"])  # guard bad rows
            filtered_df = filtered_df[
                (filtered_df["tanggal"].dt.date >= start_date)
                & (filtered_df["tanggal"].dt.date <= end_date)
            ]

            display_df = filtered_df.copy()
            display_df["tanggal"] = display_df["tanggal"].dt.strftime("%Y-%m-%d %H:%M:%S").astype(str)

            col1, col2, col3 = st.columns(3)
            with col1:
                total_tx = int(len(filtered_df))
                st.metric("Total Transaksi", total_tx)
            with col2:
                total_pendapatan = int(pd.to_numeric(filtered_df["total_harga"], errors="coerce").fillna(0).sum()) if total_tx > 0 else 0
                st.metric("Total Pendapatan", f"Rp {total_pendapatan:,.0f}")
            with col3:
                rata2 = int(pd.to_numeric(filtered_df["total_harga"], errors="coerce").fillna(0).mean()) if total_tx > 0 else 0
                st.metric("Rata-rata per Transaksi", f"Rp {rata2:,.0f}")

            df_to_show = display_df[["tanggal", "nama_produk", "varian", "jumlah", "total_harga"]].copy()

            gb = GridOptionsBuilder.from_dataframe(df_to_show)
            gb.configure_columns(["tanggal"], header_name="Tanggal")
            gb.configure_columns(["nama_produk"], header_name="Produk")
            gb.configure_columns(["varian"], header_name="Varian")
            gb.configure_columns(["jumlah"], header_name="Jumlah", type=["numericColumn"]) 
            gb.configure_columns(["total_harga"], header_name="Total", type=["numericColumn"], valueFormatter="'Rp ' + value.toLocaleString('id-ID') + ',-'")
            grid_options = gb.build()

            AgGrid(
                df_to_show,
                gridOptions=grid_options,
                height=400,
                width="100%",
                theme="streamlit",
                fit_columns_on_grid_load=True,
                allow_unsafe_jscode=True,
            )

            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Unduh Laporan Penjualan (CSV)",
                data=csv,
                file_name=f"laporan_penjualan_{start_date}_{end_date}.csv",
                mime="text/csv",
            )
        else:
            st.info("Belum ada data penjualan")

    with tab_pred:
        st.subheader("Laporan Prediksi (Sederhana)")
        sales_df = db.get_sales_data()
        if sales_df.empty:
            st.info("Belum ada data penjualan untuk menghitung prediksi.")
        else:
            sales_df["tanggal"] = pd.to_datetime(sales_df["tanggal"], errors="coerce")
            sales_df = sales_df.dropna(subset=["tanggal"]) 
            sales_df["tahun_bulan"] = sales_df["tanggal"].dt.to_period("M").astype(str)

            produk_list = sorted(sales_df["nama_produk"].dropna().unique().tolist())
            col1, col2 = st.columns(2)
            with col1:
                produk = st.selectbox("Pilih Produk", produk_list)
            with col2:
                horizon = st.slider("Horizon (bulan)", 1, 6, 3)

            dfp = sales_df[sales_df["nama_produk"] == produk].copy()
            if dfp.empty:
                st.info("Tidak ada data untuk produk ini.")
            else:
                monthly = dfp.groupby("tahun_bulan")["jumlah"].sum().reset_index()
                monthly["tahun_bulan_dt"] = pd.to_datetime(monthly["tahun_bulan"])
                monthly = monthly.sort_values("tahun_bulan_dt")

                avg3 = monthly["jumlah"].tail(3).mean() if len(monthly) >= 1 else 0
                future_periods = pd.date_range(
                    start=(monthly["tahun_bulan_dt"].max() + pd.offsets.MonthBegin(1)), periods=horizon, freq="MS"
                ) if not monthly.empty else pd.date_range(start=pd.Timestamp.today().normalize() + pd.offsets.MonthBegin(0), periods=horizon, freq="MS")

                forecast_df = pd.DataFrame({
                    "Bulan": future_periods.strftime("%Y-%m"),
                    "Prediksi_Jumlah": [int(round(avg3))] * len(future_periods)
                })

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Rata-rata 3 Bulan Terakhir", f"{avg3:,.0f} unit")
                with col2:
                    st.metric("Total Prediksi", f"{forecast_df['Prediksi_Jumlah'].sum():,.0f} unit")

                hist = monthly[["tahun_bulan_dt", "jumlah"]].rename(columns={"tahun_bulan_dt": "Bulan", "jumlah": "Jumlah"})
                hist["Tipe"] = "Aktual"
                fut = forecast_df.copy()
                fut["Bulan"] = pd.to_datetime(fut["Bulan"]) 
                fut = fut.rename(columns={"Prediksi_Jumlah": "Jumlah"})
                fut["Tipe"] = "Prediksi"
                chart_df = pd.concat([hist, fut], ignore_index=True)

                fig = px.line(chart_df, x="Bulan", y="Jumlah", color="Tipe", markers=True, title=f"Aktual vs Prediksi - {produk}")
                st.plotly_chart(fig, use_container_width=True)

                st.download_button(
                    label="Unduh Prediksi (CSV)",
                    data=forecast_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"laporan_prediksi_{produk}.csv",
                    mime="text/csv",
                )

    with tab_users:
        st.subheader("Laporan Data User")
        if hasattr(db, 'get_users'):
            users_df = db.get_users()
            if users_df.empty:
                st.info("Belum ada data user.")
            else:
                gb = GridOptionsBuilder.from_dataframe(users_df)
                gb.configure_default_column(resizable=True, filter=True, sortable=True)
                gb.configure_grid_options(domLayout="autoHeight", pagination=True, paginationPageSize=10)
                grid_options = gb.build()
                AgGrid(users_df, gridOptions=grid_options, theme='streamlit', height=400, fit_columns_on_grid_load=True)

                st.download_button(
                    label="Unduh Data User (CSV)",
                    data=users_df.to_csv(index=False),
                    file_name="laporan_data_user.csv",
                    mime="text/csv",
                )
        else:
            st.warning("Fungsi get_users() belum tersedia di DatabaseManager. Restart aplikasi setelah update, atau hubungi admin.")

    with tab_abc:
        st.subheader("Laporan Kinerja Produk")
        sales_df = db.get_sales_data()
        if sales_df.empty:
            st.info("Belum ada data penjualan.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Dari Tanggal", value=datetime.now().date() - timedelta(days=90), key="abc_start")
            with c2:
                end_date = st.date_input("Sampai Tanggal", value=datetime.now().date(), key="abc_end")

            sdf = sales_df.copy()
            sdf["tanggal"] = pd.to_datetime(sdf["tanggal"], errors="coerce")
            sdf = sdf.dropna(subset=["tanggal"]) 
            sdf = sdf[(sdf["tanggal"].dt.date >= start_date) & (sdf["tanggal"].dt.date <= end_date)]

            agg = sdf.groupby(["nama_produk", "varian"], dropna=False)["total_harga"].sum().reset_index()
            agg = agg.sort_values("total_harga", ascending=False)
            total = agg["total_harga"].sum()
            agg["persen"] = agg["total_harga"] / total
            agg["kumulatif"] = agg["persen"].cumsum()
            agg["kategori"] = pd.cut(
                agg["kumulatif"],
                bins=[-0.01, 0.80, 0.95, 1.0],
                labels=["A", "B", "C"]
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pendapatan", f"Rp {int(total):,}")
            with col2:
                st.metric("Jumlah Produk", len(agg))
            with col3:
                counts = agg["kategori"].value_counts().to_dict()
                st.metric("Distribusi", f"A:{counts.get('A',0)} B:{counts.get('B',0)} C:{counts.get('C',0)}")

            gb = GridOptionsBuilder.from_dataframe(agg)
            gb.configure_default_column(resizable=True, filter=True, sortable=True)
            gb.configure_columns(["total_harga"], header_name="Total", type=["numericColumn"], valueFormatter="'Rp ' + value.toLocaleString('id-ID') + ',-'")
            gb.configure_columns(["persen", "kumulatif"], type=["numericColumn"], valueFormatter="(value*100).toFixed(2) + '%'")
            grid_options = gb.build()
            AgGrid(agg, gridOptions=grid_options, theme='streamlit', height=450, fit_columns_on_grid_load=True)

            fig = px.bar(agg.head(20), x="nama_produk", y="total_harga", title="Top Produk berdasarkan Pendapatan (Top 20)")
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="Unduh Laporan Kinerja Produk (CSV)",
                data=agg.to_csv(index=False),
                file_name=f"laporan_kinerja_produk_{start_date}_{end_date}.csv",
                mime="text/csv",
            )
