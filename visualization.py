import plotly.graph_objs as go
import plotly.io as pio

def to_plotly_figure(x, y, xlabel, ylabel, title, kind="bar"):
    """
    Erzeugt ein Plotly-Chart (als HTML-Snippet) für das Dashboard.
    kind: 'bar', 'line' oder 'pie'
    """
    fig = go.Figure()
    if kind == "bar":
        fig.add_trace(go.Bar(x=x, y=y))
    elif kind == "line":
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines+markers'))
    elif kind == "pie":
        fig = go.Figure(go.Pie(labels=x, values=y))
    else:
        fig.add_trace(go.Bar(x=x, y=y))
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        title=title,
        template="simple_white"
    )
    return pio.to_html(fig, full_html=False)
