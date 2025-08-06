import plotly.graph_objects as go
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'storage', 'data', 'DB'))
from DB_API import TopicsDB

def create_radar_chart():
    # Colors
    BG_COLOR, CONTAINER_BG, TEXT_FIELD_BG, TEXT_COLOR, BLACK_TEXT = "#4a4a4a", "#bcb8b1", "#e0e0e0", "#2e2e2e", "#2e2e2e"
    
    # Get data from database
    df = pd.DataFrame(TopicsDB().get_all_topics())
    df['time_spend'] = pd.to_numeric(df['time_spend'], errors='coerce').fillna(0)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= datetime.now() - timedelta(days=7)]
    
    if df.empty:
        print("No data found for the last 7 days.")
        return None
    
    topic_stats = df.groupby('topic_name')['time_spend'].sum().sort_values(ascending=False).head(5)
    if len(topic_stats) < 2:
        print("Not enough topics for a radar chart.")
        return None
    
    topics, values = topic_stats.index.tolist(), topic_stats.values.tolist()
    
    # Create radar chart
    fig = go.Figure(data=go.Scatterpolar(
        r=values, theta=topics, fill='toself', name='Time Spent',
        line_color=CONTAINER_BG, fillcolor=f'rgba(188, 184, 177, 0.3)', line_width=3
    ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, values], gridcolor=TEXT_FIELD_BG, 
                           linecolor=CONTAINER_BG, tickfont=dict(color=BLACK_TEXT), tickcolor=BLACK_TEXT),
            angularaxis=dict(gridcolor=TEXT_FIELD_BG, linecolor=CONTAINER_BG, 
                           tickfont=dict(color=TEXT_COLOR, size=12, weight='bold'), tickcolor=TEXT_COLOR),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', width=800, height=600
    )
    
    # Save
    temp_dir = "./storage/temp/"
    os.makedirs(temp_dir, exist_ok=True)
    save_path = os.path.join(temp_dir, "radar_chart_7days.png")
    fig.write_image(save_path, width=800, height=600)
    return save_path

def get_radar_chart_path():
    return create_radar_chart()
