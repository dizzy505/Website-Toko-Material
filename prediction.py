import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

class SalesPredictor:
    """Prediksi penjualan material menggunakan regresi linear"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def _prepare_features(self, df):
        """Prepare features for the model"""
        if df.empty:
            return pd.DataFrame()
            
        # Convert date to datetime and extract features
        df['tanggal'] = pd.to_datetime(df['tanggal'])
        df = df.sort_values('tanggal')
        
        # Basic time features
        df['day_of_week'] = df['tanggal'].dt.dayofweek
        df['day_of_month'] = df['tanggal'].dt.day
        df['month'] = df['tanggal'].dt.month
        df['day_of_year'] = df['tanggal'].dt.dayofyear
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Add lag features (previous day's sales)
        df['prev_day_sales'] = df['jumlah'].shift(1).fillna(0)
        
        return df
    
    def _fallback_prediction(self, product, days_ahead, reason):
        default_qty = 1
        
        sales_data = self.db.get_sales_history(
            product_id=product.get('id'), 
            days_back=30
        )
        
        if sales_data is not None and not sales_data.empty:
            default_qty = sales_data['jumlah'].mean() or default_qty
        
        predictions = []
        for i in range(1, days_ahead + 1):
            predictions.append({
                'tanggal': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                'predicted_sales': round(default_qty, 2),
                'confidence': 'rendah',
                'method': f'fallback_{reason}',
                'produk_id': product.get('id', 0),
                'nama_produk': product.get('nama_produk', 'Tidak Diketahui'),
                'varian': product.get('varian', '')
            })
            
        return predictions, product
    
    def _aggregate_daily_to_monthly(self, daily_predictions):
        if not daily_predictions:
            return None
            
        df = pd.DataFrame(daily_predictions)
        
        df['tanggal'] = pd.to_datetime(df['tanggal'])
        df['tahun_bulan'] = df['tanggal'].dt.to_period('M')
        
        monthly = df.groupby('tahun_bulan').agg(
            total_penjualan=('predicted_sales', 'sum'),
            rata_harian=('predicted_sales', 'mean')
        ).reset_index()
        
        monthly['tahun_bulan'] = monthly['tahun_bulan'].astype(str)
        
        return monthly.to_dict('records')
    
    def predict_sales(self, product_id, days_ahead=30):
        try:
            products_df = self.db.get_products()
            if products_df is None or products_df.empty:
                fallback_preds, product_info = self._fallback_prediction(
                    {'id': product_id, 'nama_produk': 'Unknown', 'varian': '', 'stok_awal': 1}, 
                    days_ahead, 
                    'no_products'
                )
                
                monthly_forecast = self._aggregate_daily_to_monthly(fallback_preds)
                
                return fallback_preds, product_info, monthly_forecast
                
            product = products_df[products_df['id'] == product_id].iloc[0].to_dict()
            
            sales_df = self.db.get_sales_data()
            if sales_df is None or sales_df.empty:
                fallback_pred = self._fallback_prediction(product, days_ahead, 'no_sales_data')
                return fallback_pred[0], fallback_pred[1], None
                
            product_sales = sales_df[sales_df['product_id'] == product_id].copy()
            product_sales = sales_df[sales_df['product_id'] == product_id].copy()
            if product_sales.empty:
                fallback_pred = self._fallback_prediction(product, days_ahead, 'no_product_sales')
                return fallback_pred[0], fallback_pred[1], None
                
            df = self._prepare_features(product_sales)
            if df.empty:
                fallback_pred = self._fallback_prediction(product, days_ahead, 'feature_prep_failed')
                return fallback_pred[0], fallback_pred[1], None
            
            avg_daily_sales = df['jumlah'].mean()
            
            if len(df) < 30:
                predictions = []
                for i in range(1, days_ahead + 1):
                    pred_date = datetime.now() + timedelta(days=i)
                    predictions.append({
                        'tanggal': pred_date.strftime('%Y-%m-%d'),
                        'predicted_sales': max(1, round(avg_daily_sales, 2)),
                        'confidence': 'sedang',
                        'method': 'rata_rata_sederhana',
                        'produk_id': product_id,
                        'nama_produk': product.get('nama_produk', 'Tidak Diketahui'),
                        'varian': product.get('varian', '')
                    })
                
                monthly_forecast = self._aggregate_daily_to_monthly(predictions)
                return predictions, product, monthly_forecast
            
            feature_cols = ['day_of_week', 'day_of_month', 'month', 'is_weekend', 'prev_day_sales']
            X = df[feature_cols]
            y = df['jumlah']
            
            X_scaled = self.scaler.fit_transform(X)
            
            self.model.fit(X_scaled, y)
            
            last_date = df['tanggal'].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, days_ahead + 1)]
            
            future_df = pd.DataFrame({
                'tanggal': future_dates,
                'day_of_week': [d.weekday() for d in future_dates],
                'day_of_month': [d.day for d in future_dates],
                'month': [d.month for d in future_dates],
                'is_weekend': [1 if d.weekday() >= 5 else 0 for d in future_dates],
                'prev_day_sales': [df['jumlah'].iloc[-1]] + [0] * (days_ahead - 1)
            })
            
            X_future = future_df[feature_cols]
            X_future_scaled = self.scaler.transform(X_future)
            predictions_values = self.model.predict(X_future_scaled)
            predictions_values = [max(0, p) for p in predictions_values]
            
            predictions = []
            for i in range(days_ahead):
                predictions.append({
                    'tanggal': future_dates[i].strftime('%Y-%m-%d'),
                    'predicted_sales': round(predictions_values[i], 2),
                    'confidence': 'tinggi',
                    'method': 'regresi_linear',
                    'produk_id': product_id,
                    'nama_produk': product.get('nama_produk', 'Tidak Diketahui'),
                    'varian': product.get('varian', '')
                })
            
            monthly_forecast = self._aggregate_daily_to_monthly(predictions)
                
            return predictions, product, monthly_forecast
            
        except Exception as e:
            print(f"Error in predict_sales: {e}")
            product = self.db.get_product_by_id(product_id)
            if not product:
                fallback_pred = self._fallback_prediction(
                    {'id': product_id, 'nama_produk': 'Tidak Diketahui', 'stok_awal': 1},
                    days_ahead,
                    'produk_tidak_ditemukan'
                )
                return fallback_pred[0], fallback_pred[1], None
                
            sales_data = self.db.get_sales_history(product_id=product_id, days_back=90)
            if sales_data is None or sales_data.empty:
                fallback_pred = self._fallback_prediction(product, days_ahead, 'tidak_ada_data_penjualan')
                return fallback_pred[0], fallback_pred[1], None
                
            sales_data['tanggal'] = pd.to_datetime(sales_data['tanggal'])
            sales_data = sales_data.sort_values('tanggal')
            
            df = sales_data.copy()
            df = self._prepare_features(df)
            
            if len(df) < 7:
                avg_sales = df['jumlah'].mean() if not df.empty else product.get('stok_awal', 1)
                predictions = []
                for i in range(1, days_ahead + 1):
                    predictions.append({
                        'tanggal': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                        'predicted_sales': round(avg_sales, 2),
                        'confidence': 'rendah',
                        'method': 'rata_rata_sederhana',
                        'produk_id': product_id,
                        'nama_produk': product.get('nama_produk', 'Tidak Diketahui'),
                        'varian': product.get('varian', '')
                    })
                return predictions, product
            
            window = min(7, len(df))
            avg_sales = df['jumlah'].tail(window).mean()
            
            predictions = []
            last_date = df['tanggal'].max()
            
            for i in range(1, days_ahead + 1):
                pred_date = last_date + timedelta(days=i)
                predictions.append({
                    'tanggal': pred_date.strftime('%Y-%m-%d'),
                    'predicted_sales': round(avg_sales, 2),
                    'confidence': 'sedang',
                    'method': 'rata_rata_bergerak',
                    'produk_id': product_id,
                    'nama_produk': product.get('nama_produk', 'Tidak Diketahui'),
                    'varian': product.get('varian', '')
                })
                
            return predictions, product
            
        except Exception as e:
            print(f"Error in predict_sales: {str(e)}")
            if 'product' not in locals():
                product = {'id': product_id, 'nama_produk': 'Tidak Diketahui', 'stok_awal': 1}
            return self._fallback_prediction(
                product,
                days_ahead,
                f'error: {str(e)}'
            )
    
    def get_restock_recommendations(self):
        try:
            products_df = self.db.get_products()
            if products_df is None or products_df.empty:
                return []
            
            recommendations = []
            
            for _, product in products_df.iterrows():
                product_id = product['id']
                current_stock = 0
                min_stock = 0
                
                predictions, _ = self.predict_demand(product_id, 30)
                if not predictions:
                    continue
                
                total_predicted = sum(p['predicted_demand'] for p in predictions)
                
                safety_stock = total_predicted * 0.2
                
                required_stock = total_predicted + safety_stock
                recommended_order = max(0, required_stock)
                
                if required_stock > 0:
                    avg_daily = total_predicted / 30 if total_predicted > 0 else 0
                    if avg_daily >= 10:
                        urgency = 'High'
                    elif avg_daily >= 5:
                        urgency = 'Medium'
                    else:
                        urgency = 'Low'
                    
                    method = predictions[0].get('method', 'unknown')
                    confidence = predictions[0].get('confidence', 'medium')
                    
                    recommendations.append({
                        'product_id': product_id,
                        'nama_produk': product['nama_produk'],
                        'varian': product.get('varian', ''),
                        'predicted_demand_30days': round(total_predicted, 2),
                        'recommended_order': round(recommended_order),
                        'confidence': confidence,
                        'method': method,
                        'urgency': urgency
                    })
            
            urgency_order = {'High': 0, 'Medium': 1, 'Low': 2}
            return sorted(recommendations, 
                        key=lambda x: (urgency_order[x['urgency']], -x['recommended_order']))
            
        except Exception as e:
            print(f"Error in get_restock_recommendations: {e}")
            return []
    
    def create_sales_chart(self, product_id, days_ahead=30):
        try:
            hist_data = self.db.get_sales_history(product_id=product_id, days_back=90)
            if hist_data is None or hist_data.empty:
                return None
                
            predictions, _, _ = self.predict_sales(product_id, days_ahead)  # Mengambil 3 return values
            if not predictions:
                return None
                
            hist_data['tanggal'] = pd.to_datetime(hist_data['tanggal'])
            hist_data = hist_data.sort_values('tanggal')
            
            pred_df = pd.DataFrame(predictions)
            pred_df['tanggal'] = pd.to_datetime(pred_df['tanggal'])
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_data['tanggal'],
                y=hist_data['jumlah'],
                mode='lines+markers',
                name='Riwayat Penjualan',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=pred_df['tanggal'],
                y=pred_df['predicted_sales'],
                mode='lines+markers',
                name='Prediksi Penjualan',
                line=dict(color='#ff7f0e', dash='dash', width=2),
                marker=dict(size=6, symbol='diamond')
            ))
            
            product_info = self.db.get_product_by_id(product_id)
            product_name = product_info.get('nama_produk', 'Produk') if product_info else 'Produk'
            
            fig.update_layout(
                title=f'Prediksi Penjualan {product_name}',
                xaxis_title='Tanggal',
                yaxis_title='Jumlah Terjual',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                ),
                hovermode='x unified',
                template='plotly_white',
                margin=dict(l=50, r=50, t=80, b=50),
                plot_bgcolor='rgba(0,0,0,0.02)',
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='lightgray',
                    rangemode='tozero'  # Mulai sumbu y dari 0
                )
            )
            
            if predictions and 'method' in predictions[0]:
                method_map = {
                    'regresi_linear': 'Regresi Linear',
                    'rata_rata_bergerak': 'Rata-rata Bergerak',
                    'rata_rata_sederhana': 'Rata-rata Sederhana',
                    'fallback': 'Estimasi'
                }
                method = predictions[0].get('method', 'fallback')
                confidence = predictions[0].get('confidence', 'sedang')
                
                fig.add_annotation(
                    x=0.02,
                    y=1.08,
                    xref='paper',
                    yref='paper',
                    text=f"Metode: {method_map.get(method.split('_')[0], method)} | "
                         f"Tingkat Kepercayaan: {confidence.capitalize()}",
                    showarrow=False,
                    font=dict(size=12, color='gray')
                )
            
            return fig
            
        except Exception as e:
            print(f"Gagal membuat grafik penjualan: {e}")
            return None
    
    def get_sales_trends(self):
        try:
            sales_df = self.db.get_sales_data()
            if sales_df is None or sales_df.empty:
                return None
                
            sales_df['tanggal'] = pd.to_datetime(sales_df['tanggal'])
            sales_df['tanggal'] = pd.to_datetime(sales_df['tanggal'])
            
            sales_df['year_month'] = sales_df['tanggal'].dt.strftime('%Y-%m')
            monthly_trends = sales_df.groupby('year_month')['jumlah'].sum().reset_index()
            
            top_products = sales_df.groupby('product_id')['jumlah'].sum().nlargest(5)
            
            return {
                'monthly_trends': monthly_trends,
                'top_products': top_products
            }
            
        except Exception as e:
            print(f"Error in get_sales_trends: {e}")
            return None
