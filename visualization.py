import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def plot_winning_numbers_frequency(df):
    """
    Create a bar chart showing the frequency of each winning number
    
    Args:
        df: DataFrame containing TOTO results
    
    Returns:
        Plotly figure object
    """
    # Extract all winning numbers from the dataframe
    all_numbers = []
    for numbers in df['winning_numbers']:
        if isinstance(numbers, list):
            all_numbers.extend(numbers)
    
    # Count frequency of each number
    number_counts = pd.Series(all_numbers).value_counts().reset_index()
    number_counts.columns = ['Number', 'Frequency']
    number_counts = number_counts.sort_values('Number')
    
    # Create bar chart
    fig = px.bar(
        number_counts, 
        x='Number', 
        y='Frequency',
        labels={'Number': 'TOTO Number', 'Frequency': 'Frequency'},
        title='Frequency of Winning Numbers',
        color='Frequency',
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        xaxis=dict(tickmode='linear', dtick=5),
        height=500
    )
    
    return fig

def plot_prize_pool_trend(df):
    """
    Create a line chart showing prize pool trends over time
    
    Args:
        df: DataFrame containing TOTO results with prize pool calculations
    
    Returns:
        Plotly figure object
    """
    # Ensure data is sorted by date
    plot_df = df.sort_values('draw_date')
    
    # Create figure with multiple traces
    fig = go.Figure()
    
    # Add estimated prize pool
    fig.add_trace(go.Scatter(
        x=plot_df['draw_date'],
        y=plot_df['estimated_prize_pool'],
        mode='lines+markers',
        name='Estimated Prize Pool',
        line=dict(color='green', width=2)
    ))
    
    # Add Group 1 prize when there are winners
    group1_with_winners = plot_df[plot_df['group_1_winners'] > 0]
    if not group1_with_winners.empty:
        fig.add_trace(go.Scatter(
            x=group1_with_winners['draw_date'],
            y=group1_with_winners['group_1_prize'],
            mode='markers',
            name='Group 1 Prize',
            marker=dict(color='red', size=10)
        ))
    
    # Add expected Group 1 prize (including rollovers)
    fig.add_trace(go.Scatter(
        x=plot_df['draw_date'],
        y=plot_df['expected_group1_prize'],
        mode='lines',
        name='Expected Group 1 Prize',
        line=dict(color='purple', width=2, dash='dash')
    ))
    
    # Update layout
    fig.update_layout(
        title='Prize Pool Trends Over Time',
        xaxis_title='Draw Date',
        yaxis_title='Amount (SGD)',
        height=500,
        hovermode='x unified',
        yaxis=dict(rangemode='tozero')
    )
    
    # Format y-axis values as currency
    fig.update_yaxes(tickprefix='$', tickformat=',.0f')
    
    return fig

def plot_winning_numbers_heatmap(df):
    """
    Create a heatmap showing patterns in winning numbers
    
    Args:
        df: DataFrame containing TOTO results
    
    Returns:
        Plotly figure object
    """
    # Create a matrix to store draw number vs. number appearance
    matrix = np.zeros((49, len(df)))
    
    for i, (_, row) in enumerate(df.iterrows()):
        if isinstance(row['winning_numbers'], list):
            for num in row['winning_numbers']:
                if 1 <= num <= 49:
                    matrix[num-1, i] = 1
            
            # Mark additional number differently
            if row['additional_number'] and 1 <= row['additional_number'] <= 49:
                matrix[row['additional_number']-1, i] = 2
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix,
        x=[i+1 for i in range(len(df))],
        y=[i+1 for i in range(49)],
        colorscale=[
            [0, 'white'],
            [0.5, 'green'],
            [1, 'red']
        ],
        showscale=False
    ))
    
    fig.update_layout(
        title='Winning Numbers Pattern',
        xaxis_title='Draw Index',
        yaxis_title='Number',
        height=700,
        yaxis=dict(
            tickmode='linear',
            dtick=5,
            autorange='reversed'
        )
    )
    
    return fig

def plot_group_prize_distribution(df):
    """
    Create a box plot showing the distribution of prizes for each group
    
    Args:
        df: DataFrame containing TOTO results
    
    Returns:
        Plotly figure object
    """
    # Prepare data for plotting
    prize_data = []
    
    for group in range(1, 8):
        group_col = f'group_{group}_prize'
        winners_col = f'group_{group}_winners'
        
        # Only include data points where there were winners
        valid_prizes = df[df[winners_col] > 0][group_col]
        
        for prize in valid_prizes:
            prize_data.append({
                'Group': f'Group {group}',
                'Prize': prize
            })
    
    prize_df = pd.DataFrame(prize_data)
    
    # Create box plot
    fig = px.box(
        prize_df,
        x='Group',
        y='Prize',
        title='Distribution of Prizes by Group',
        color='Group',
        height=600
    )
    
    # Format y-axis as currency
    fig.update_yaxes(tickprefix='$', tickformat=',.0f')
    
    # Update layout
    fig.update_layout(
        xaxis_title='',
        yaxis_title='Prize Amount (SGD)',
        yaxis=dict(type='log')  # Use log scale due to large range
    )
    
    return fig
