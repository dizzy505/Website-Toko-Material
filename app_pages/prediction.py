import streamlit as st
import pandas as pd


def render(db, predictor):
    st.header("Prediksi Penjualan Bulanan")

    products_df = db.get_products()

    if products_df.empty:
        st.warning("Belum ada data produk untuk prediksi.")
        return

    st.subheader("Prediksi Penjualan Bulan Depan")

    selected_product = st.selectbox(
        "Pilih Produk",
        options=products_df['id'].tolist(),
        format_func=lambda x: f"{products_df[products_df['id']==x]['nama_produk'].iloc[0]} - {products_df[products_df['id']==x]['varian'].iloc[0]}",
        key="selected_product",
    )

    days_ahead = 30

    if st.button("Prediksi Penjualan Bulan Depan", type="primary", use_container_width=True):
        with st.spinner("Memproses prediksi..."):
            try:
                predictions, product_info, monthly_forecast = predictor.predict_sales(selected_product, days_ahead)

                if predictions is None or not predictions:
                    st.warning("Tidak dapat membuat prediksi. Data penjualan tidak mencukupi.")
                    return

                if not isinstance(predictions, list):
                    if isinstance(predictions, dict):
                        predictions = [predictions]
                    else:
                        st.warning("Format prediksi tidak valid.")
                        return

                if monthly_forecast:
                    st.markdown("---")
                    st.subheader("Prediksi Bulan Depan")

                    monthly_df = pd.DataFrame(monthly_forecast)
                    monthly_df['Bulan'] = pd.to_datetime(monthly_df['tahun_bulan']).dt.strftime('%B %Y')

                    total_penjualan = monthly_df['total_penjualan'].sum()
                    harga_jual = products_df[products_df['id'] == selected_product]['harga'].values[0]
                    total_keuntungan = total_penjualan * harga_jual

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Prediksi Penjualan", f"{total_penjualan:,.0f} unit", help="Total penjualan yang diprediksi untuk bulan depan")
                    with col2:
                        st.metric("Perkiraan Keuntungan Kotor", f"Rp {total_keuntungan:,.0f}", help="Perkiraan keuntungan kotor berdasarkan harga jual saat ini")

                    fig = predictor.create_sales_chart(selected_product, 30)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                    csv = monthly_df[['Bulan', 'total_penjualan', 'rata_harian']]
                    csv = csv.rename(columns={'total_penjualan': 'total_penjualan_unit', 'rata_harian': 'rata_harian_unit'})
                    csv['total_keuntungan'] = csv['total_penjualan_unit'] * harga_jual

                    st.download_button(
                        label="Unduh Prediksi",
                        data=csv.to_csv(index=False, float_format='%.2f').encode('utf-8'),
                        file_name=f"prediksi_penjualan_{products_df[products_df['id'] == selected_product]['nama_produk'].values[0]}.csv",
                        mime='text/csv',
                    )
                else:
                    st.warning("Tidak dapat membuat prediksi bulanan. Data tidak mencukupi.")

            except Exception as e:
                st.error(f"Terjadi kesalahan saat memproses prediksi: {str(e)}")
                st.error("Silakan coba lagi atau hubungi administrator jika masalah berlanjut.")
