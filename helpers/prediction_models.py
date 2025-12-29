import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Algorithm 1: Simple Moving Average with Trend
def simple_moving_average_prediction(data, target_column, weeks_ahead=3, window_size=4):
    """
    Simple Moving Average with trend adjustment for time series prediction
    
    Args:
        data: DataFrame with time series data
        target_column: Column name to predict
        weeks_ahead: Number of weeks to predict ahead
        window_size: Size of moving average window
    
    Returns:
        DataFrame with predictions
    """
    try:
        # Sort by year and week
        df = data.copy()
        df = df.sort_values(['Año', 'Semana'])
        
        # Ensure numeric data types
        df['Año'] = pd.to_numeric(df['Año'], errors='coerce')
        df['Semana'] = pd.to_numeric(df['Semana'], errors='coerce')
        df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna(subset=['Año', 'Semana', target_column])
        
        if len(df) < 2:
            return pd.DataFrame()
        
        # Calculate moving average
        ma_values = df[target_column].rolling(window=window_size, min_periods=1).mean()
        
        # Calculate trend (slope of recent values)
        recent_values = df[target_column].tail(window_size).values
        if len(recent_values) >= 2:
            trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
        else:
            trend = 0
        
        # Get last known value and moving average
        last_value = df[target_column].iloc[-1]
        last_ma = ma_values.iloc[-1]
        
        # Generate predictions
        predictions = []
        last_year = int(df['Año'].iloc[-1])
        last_week = int(df['Semana'].iloc[-1])
        
        for i in range(1, weeks_ahead + 1):
            # Calculate next week
            next_week = last_week + i
            next_year = last_year
            
            # Handle year transition
            if next_week > 52:
                next_week = next_week - 52
                next_year += 1
            
            # Predict using moving average + trend
            prediction = last_ma + (trend * i)
            prediction = max(0, prediction)  # Ensure non-negative
            
            predictions.append({
                'Año': next_year,
                'Semana': next_week,
                'Prediction': prediction,
                'Algorithm': 'Moving Average + Trend'
            })
        
        return pd.DataFrame(predictions)
    
    except Exception as e:
        print(f"Error in Moving Average prediction: {e}")
        return pd.DataFrame()

# Algorithm 2: Exponential Smoothing (Holt-Winters)
def exponential_smoothing_prediction(data, target_column, weeks_ahead=3, alpha=0.3, beta=0.1):
    """
    Exponential Smoothing with trend for time series prediction
    
    Args:
        data: DataFrame with time series data
        target_column: Column name to predict
        weeks_ahead: Number of weeks to predict ahead
        alpha: Smoothing parameter for level
        beta: Smoothing parameter for trend
    
    Returns:
        DataFrame with predictions
    """
    try:
        df = data.copy()
        df = df.sort_values(['Año', 'Semana'])
        
        # Ensure numeric data types
        df['Año'] = pd.to_numeric(df['Año'], errors='coerce')
        df['Semana'] = pd.to_numeric(df['Semana'], errors='coerce')
        df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna(subset=['Año', 'Semana', target_column])
        
        values = df[target_column].values
        
        if len(values) < 2:
            return pd.DataFrame()
        
        # Initialize level and trend
        level = values[0]
        trend = values[1] - values[0] if len(values) > 1 else 0
        
        # Apply exponential smoothing
        for i in range(1, len(values)):
            new_level = alpha * values[i] + (1 - alpha) * (level + trend)
            trend = beta * (new_level - level) + (1 - beta) * trend
            level = new_level
        
        # Generate predictions
        predictions = []
        last_year = int(df['Año'].iloc[-1])
        last_week = int(df['Semana'].iloc[-1])
        
        for i in range(1, weeks_ahead + 1):
            # Calculate next week
            next_week = last_week + i
            next_year = last_year
            
            # Handle year transition
            if next_week > 52:
                next_week = next_week - 52
                next_year += 1
            
            # Predict using exponential smoothing
            prediction = level + (trend * i)
            prediction = max(0, prediction)  # Ensure non-negative
            
            predictions.append({
                'Año': next_year,
                'Semana': next_week,
                'Prediction': prediction,
                'Algorithm': 'Exponential Smoothing'
            })
        
        return pd.DataFrame(predictions)
    
    except Exception as e:
        print(f"Error in Exponential Smoothing prediction: {e}")
        return pd.DataFrame()

# Algorithm 3: Linear Regression with Seasonal Decomposition
def linear_regression_prediction(data, target_column, weeks_ahead=3):
    """
    Linear Regression with seasonal decomposition for time series prediction
    
    Args:
        data: DataFrame with time series data
        target_column: Column name to predict
        weeks_ahead: Number of weeks to predict ahead
    
    Returns:
        DataFrame with predictions
    """
    try:
        df = data.copy()
        df = df.sort_values(['Año', 'Semana'])
        
        # Ensure numeric data types
        df['Año'] = pd.to_numeric(df['Año'], errors='coerce')
        df['Semana'] = pd.to_numeric(df['Semana'], errors='coerce')
        df[target_column] = pd.to_numeric(df[target_column], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna(subset=['Año', 'Semana', target_column])
        
        if len(df) < 4:
            return pd.DataFrame()
        
        # Create time index
        df['time_index'] = range(len(df))
        
        # Simple linear regression
        X = df['time_index'].values.reshape(-1, 1)
        y = df[target_column].values
        
        # Calculate linear regression coefficients
        n = len(X)
        sum_x = np.sum(X)
        sum_y = np.sum(y)
        sum_xy = np.sum(X * y.reshape(-1, 1))
        sum_x2 = np.sum(X ** 2)
        
        # Calculate slope and intercept
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        intercept = (sum_y - slope * sum_x) / n
        
        # Generate predictions
        predictions = []
        last_year = int(df['Año'].iloc[-1])
        last_week = int(df['Semana'].iloc[-1])
        last_time_index = df['time_index'].iloc[-1]
        
        for i in range(1, weeks_ahead + 1):
            # Calculate next week
            next_week = last_week + i
            next_year = last_year
            
            # Handle year transition
            if next_week > 52:
                next_week = next_week - 52
                next_year += 1
            
            # Predict using linear regression
            next_time_index = last_time_index + i
            prediction = intercept + slope * next_time_index
            prediction = max(0, prediction)  # Ensure non-negative
            
            predictions.append({
                'Año': next_year,
                'Semana': next_week,
                'Prediction': prediction,
                'Algorithm': 'Linear Regression'
            })
        
        return pd.DataFrame(predictions)
    
    except Exception as e:
        print(f"Error in Linear Regression prediction: {e}")
        return pd.DataFrame()

# Main function to run all algorithms
def predict_kg_values(data, target_columns=['KG_PROCESADOS', 'KG_EXPORTABLES'], weeks_ahead=3):
    """
    Run all prediction algorithms for specified columns
    
    Args:
        data: DataFrame with time series data
        target_columns: List of column names to predict
        weeks_ahead: Number of weeks to predict ahead
    
    Returns:
        Dictionary with predictions for each algorithm and column
    """
    results = {}
    
    for column in target_columns:
        if column not in data.columns:
            print(f"Column {column} not found in data")
            continue
            
        column_results = {}
        
        # Run all algorithms
        ma_predictions = simple_moving_average_prediction(data, column, weeks_ahead)
        es_predictions = exponential_smoothing_prediction(data, column, weeks_ahead)
        lr_predictions = linear_regression_prediction(data, column, weeks_ahead)
        
        # Store results
        column_results['Moving Average + Trend'] = ma_predictions
        column_results['Exponential Smoothing'] = es_predictions
        column_results['Linear Regression'] = lr_predictions
        
        results[column] = column_results
    
    return results

# Function to format predictions for display
def format_predictions_for_display(predictions_dict):
    """
    Format predictions for display in the dashboard
    
    Args:
        predictions_dict: Dictionary with predictions from predict_kg_values
    
    Returns:
        Formatted DataFrame for display
    """
    all_predictions = []
    
    for column, algorithms in predictions_dict.items():
        for algorithm_name, predictions_df in algorithms.items():
            if len(predictions_df) > 0:
                for _, row in predictions_df.iterrows():
                    try:
                        # Ensure numeric values
                        prediction_value = float(row['Prediction'])
                        year_value = int(row['Año'])
                        week_value = int(row['Semana'])
                        
                        all_predictions.append({
                            'Año': year_value,
                            'Semana': week_value,
                            'Columna': column,
                            'Algoritmo': algorithm_name,
                            'Predicción': f"{prediction_value:,.0f}",
                            'Valor_Numerico': prediction_value
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Error formatting prediction row: {e}")
                        continue
    
    return pd.DataFrame(all_predictions)

# Function to create prediction chart
def create_prediction_chart(historical_data, predictions_dict, target_column):
    """
    Create a chart showing historical data and predictions
    
    Args:
        historical_data: DataFrame with historical data
        predictions_dict: Dictionary with predictions
        target_column: Column name to visualize
    
    Returns:
        Plotly figure object
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Prepare historical data
        hist_df = historical_data.copy()
        hist_df = hist_df.sort_values(['Año', 'Semana'])
        
        # Ensure numeric data types for chart
        hist_df['Año'] = pd.to_numeric(hist_df['Año'], errors='coerce')
        hist_df['Semana'] = pd.to_numeric(hist_df['Semana'], errors='coerce')
        hist_df[target_column] = pd.to_numeric(hist_df[target_column], errors='coerce')
        
        # Remove any rows with NaN values
        hist_df = hist_df.dropna(subset=['Año', 'Semana', target_column])
        
        if len(hist_df) == 0:
            return None
            
        hist_df['Fecha'] = hist_df.apply(lambda x: f"{int(x['Año'])}-W{int(x['Semana']):02d}", axis=1)
        
        # Create figure
        fig = go.Figure()
        
        # Add historical data
        fig.add_trace(go.Scatter(
            x=hist_df['Fecha'],
            y=hist_df[target_column],
            mode='lines+markers',
            name='Datos Históricos',
            line=dict(color='#094782', width=2),
            marker=dict(size=6)
        ))
        
        # Add predictions for each algorithm
        colors = ['#ff7f0e', '#2ca02c', '#d62728']
        algorithms = list(predictions_dict[target_column].keys())
        
        for i, (algorithm_name, predictions_df) in enumerate(predictions_dict[target_column].items()):
            if len(predictions_df) > 0:
                pred_df = predictions_df.copy()
                pred_df['Fecha'] = pred_df.apply(lambda x: f"{int(x['Año'])}-W{int(x['Semana']):02d}", axis=1)
                
                fig.add_trace(go.Scatter(
                    x=pred_df['Fecha'],
                    y=pred_df['Prediction'],
                    mode='lines+markers',
                    name=f'Predicción - {algorithm_name}',
                    line=dict(color=colors[i % len(colors)], width=2, dash='dash'),
                    marker=dict(size=8, symbol='diamond')
                ))
        
        # Update layout
        fig.update_layout(
            title=f'Predicciones para {target_column} - Próximas 3 Semanas',
            xaxis_title='Semana',
            yaxis_title='Valor',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=400
        )
        
        return fig
    
    except Exception as e:
        print(f"Error creating prediction chart: {e}")
        return None 