import plotly.express as px
from dash import Dash, Input, Output, dcc, html

from src import analytics
from src.generate_data import BRANCHES


def build_figures(df):
    """منفصلة عن الـ callback عشان نقدر نختبرها من غير سيرفر."""
    monthly = analytics.monthly_sales(df)
    fig_month = px.line(monthly, x="month", y="revenue", markers=True,
                        title="Monthly revenue")
    fig_branch = px.bar(analytics.by_branch(df), x="branch", y="revenue",
                        color="branch", title="Revenue by branch")
    fig_prod = px.bar(analytics.top_products(df, 8).iloc[::-1], x="revenue", y="product",
                      orientation="h", color="category", title="Top products")
    for fig in (fig_month, fig_branch, fig_prod):
        fig.update_layout(margin=dict(l=40, r=20, t=50, b=40), template="plotly_white")
    return fig_month, fig_branch, fig_prod


def kpi(label, value):
    return html.Div([html.Div(label, style={"color": "#666", "fontSize": "13px"}),
                     html.Div(value, style={"fontSize": "26px", "fontWeight": "600"})],
                    style={"padding": "12px 18px", "border": "1px solid #ddd",
                           "borderRadius": "8px", "minWidth": "150px"})


def create_app(db_path=analytics.DB_PATH):
    df0 = analytics.load_sales_cached(db_path)
    app = Dash(__name__)
    app.title = "Sales Analytics"

    app.layout = html.Div([
        html.H2("Sales Analytics Dashboard"),
        html.Div([
            dcc.Dropdown(["All"] + BRANCHES, "All", id="branch", clearable=False,
                         style={"width": "200px"}),
            dcc.DatePickerRange(id="dates", start_date=df0["order_date"].min().date(),
                                end_date=df0["order_date"].max().date(),
                                min_date_allowed=df0["order_date"].min().date(),
                                max_date_allowed=df0["order_date"].max().date()),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),
        html.Div(id="kpis", style={"display": "flex", "gap": "12px", "flexWrap": "wrap"}),
        dcc.Graph(id="monthly"),
        html.Div([dcc.Graph(id="branches", style={"flex": 1}),
                  dcc.Graph(id="products", style={"flex": 1})],
                 style={"display": "flex", "gap": "12px"}),
    ], style={"maxWidth": "1100px", "margin": "0 auto", "padding": "16px",
              "fontFamily": "Arial, sans-serif"})

    @app.callback(Output("kpis", "children"), Output("monthly", "figure"),
                  Output("branches", "figure"), Output("products", "figure"),
                  Input("branch", "value"), Input("dates", "start_date"),
                  Input("dates", "end_date"))
    def update(branch, start, end):
        df = analytics.filter_df(analytics.load_sales_cached(db_path),
                                 None if branch == "All" else branch, start, end)
        s = analytics.summary(df)
        cards = [kpi("Revenue", f"{s['revenue']:,.0f}"), kpi("Orders", f"{s['orders']:,}"),
                 kpi("Avg order", f"{s['avg_order_value']:,.0f}"),
                 kpi("Customers", f"{s['customers']:,}")]
        return (cards, *build_figures(df))

    app._update = update          # عشان الاختبار يناديه مباشرة
    return app


if __name__ == "__main__":
    create_app().run(port=8050, debug=False)
