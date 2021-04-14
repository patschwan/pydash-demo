import os
from dotenv import load_dotenv
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import requests
import mysql.connector

# Bootstrap
# https://www.bootstrapcdn.com/
# https://dash-bootstrap-components.opensource.faculty.ai/docs/
import dash_bootstrap_components as dbc


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

colors = {
    'background': '#f9f7f7',
    'text': '#112d4e'
}

# additional style elements
jumbo_style = {
    'margin-top': '40px',
    'margin-bottom': '40px',
    'background-color': '#fff'
}

ma_top = {
    'margin-top': '80px',
}


########################################
# SQL Data per MySQL driver + query
# MySQL connection config

load_dotenv()
db_user = os.getenv("DB_USER")
db_pw = os.getenv("DB_PW")
env_db = os.getenv("DB")

config = {
    'user': db_user,
    'password': db_pw,
    'host': 'pschwan.de',
    'database': env_db
}

cnx = mysql.connector.connect(**config)
mycur = cnx.cursor()


# data for charts
mycur.execute("""
    SELECT row_year, forecast, SUM(umsatz) AS umsatz, SUM(deckungsbeitrag) AS deckungsbeitrag
    FROM dp_view
    WHERE row_year IN ('2020', '2019', '2018', '2017')
    GROUP BY row_year, forecast
    ORDER BY row_year asc, forecast desc
    """)
df_sql_data = pd.DataFrame(mycur.fetchall(), columns=mycur.column_names)
# für Slider
df_sql_data['year'] = df_sql_data['row_year'].astype(int)

# data for indicators
mycur.execute("""
    SELECT forecast,
        SUM(gewinn) AS gewinn_ytd,
        SUM(umsatz) AS umsatz_ytd,
        SUM(deckungsbeitrag) AS db_ytd
    FROM dp_view
    WHERE DATEDIFF(row_dt, CURDATE()) < 0
    AND row_dt >= '2021-01-01'
    GROUP BY forecast
    ORDER BY forecast desc
    """)
df_indicator = pd.DataFrame(mycur.fetchall(), columns=mycur.column_names)
df_indicator = df_indicator.set_index(['forecast'])

# data for indicator scatter plot
mycur.execute("""
SELECT 
row_month,
SUM(gewinn) AS gewinn_ytd
FROM dp_view
WHERE row_dt <= CURDATE()
AND row_dt >= '2021-01-01'
AND forecast = 'plan'
GROUP BY row_month
ORDER BY row_month asc;
""")
df_ind_scatter = pd.DataFrame(mycur.fetchall(), columns=mycur.column_names)
# df_ind_scatter = df_indicator.set_index(['forecast'])


# Customer Program PieChart
mycur.execute("""
    SELECT COUNT(cj.cust_prog) AS 'Count', 'Yes' AS 'CustomerProg'
    FROM customers AS cj
    WHERE cj.cust_prog = 1
    UNION ALL
    SELECT COUNT(cn.cust_prog) AS 'Count', 'No' AS 'CustomerProg'
    FROM customers AS cn
    WHERE cn.cust_prog = 0;
    """)
df_cust_prog = pd.DataFrame(
    mycur.fetchall(), columns=mycur.column_names)


# Newsletter Program PieChart
mycur.execute("""
    SELECT COUNT(cj.newsletter) AS 'Count', 'Yes' AS 'Newsletter'
    FROM customers AS cj
    WHERE cj.newsletter = 1
    UNION ALL
    SELECT COUNT(cn.newsletter) AS 'Count', 'No' AS 'Newsletter'
    FROM customers AS cn
    WHERE cn.newsletter = 0;
    """)
df_newsletter = pd.DataFrame(
    mycur.fetchall(), columns=mycur.column_names)


mycur.close()

########################################
# API data
url_product = 'https://34hj8d.deta.dev/sales/groupby/product/'
r = requests.get(url_product)
json = r.json()
df_product = pd.DataFrame(json)
df_prd_grp_quantity = df_product
# für den Slider, aber muss doch geschickter gehen!
df_prd_grp_quantity['syear'] = df_prd_grp_quantity['Year'].astype(str)


# Effizienz Kundenprogramm und Newsletter
url_cust_YTD = 'https://34hj8d.deta.dev/sales/groupby/customer/2021/'
r = requests.get(url_cust_YTD)
json = r.json()
df_sales_cust = pd.DataFrame(json)
# modify for presentation layer
yn_dict = {0: "no", 1: "yes"}
df_sales_cust['Customer Program'] = df_sales_cust['Customer Program'].apply(
    lambda x: yn_dict[x])
df_sales_cust['Newsletter'] = df_sales_cust['Newsletter'].apply(
    lambda x: yn_dict[x])


url_cust_ymonth = 'https://34hj8d.deta.dev/sales/groupby/customer/month/'
r = requests.get(url_cust_ymonth)
json = r.json()
df_sales_qty = pd.DataFrame(json)
df_sales_qty['syear'] = df_sales_qty['Year'].astype(str)
df_sales_qty['smonth'] = df_sales_qty['Month'].astype(str)


# KPIs Produktgruppe
url_product_YTD = 'https://34hj8d.deta.dev/sales/groupby/product/2021/'
r = requests.get(url_product_YTD)
json = r.json()
df_prd_grp_kpi = pd.DataFrame(json)


# define labels for the Charts
labels = {'row_year': 'Year',
          'forcast': 'Forecast',
          'umsatz': 'Revenue',
          'deckungsbeitrag': 'Margin',
          'gewinn_ytd': 'Profit YTD',
          'umsatz_ytd': 'Revenue YTD',
          'db_ytd': 'Margin YTD',
          'AVG_DB_Stk': 'Avg Margin per piece',
          'smonth': 'Month',
          'syear': 'Year',
          'Descr': 'Description',
          }


########################################
# Setup Indicator
fig_ind_rev = go.Figure()
fig_ind_profit = go.Figure()
fig_ind_margin = go.Figure()
fig_ind_rev_alt = go.Figure()
# https://plotly.com/python/indicator/

fig_ind_rev.add_trace(go.Indicator(
    title="Umsatz Plan/Ist 2021 YTD",
    mode="number+delta",
    value=df_indicator.loc['ist', 'umsatz_ytd'],
    delta={'reference': df_indicator.loc['plan', 'umsatz_ytd']},
    domain={'row': 0, 'column': 0}
))

fig_ind_profit.add_trace(go.Indicator(
    title="Gewinn Plan/Ist 2021 YTD",
    mode="number+delta+gauge",
    value=df_indicator.loc['ist', 'gewinn_ytd'],
    delta={'reference': df_indicator.loc['plan', 'gewinn_ytd']},
    domain={'row': 0, 'column': 1}
))

fig_ind_rev_alt.add_trace(go.Indicator(
    title="Umsatz Plan/Ist 2021 YTD",
    mode="number+gauge",
    value=df_indicator.loc['ist', 'umsatz_ytd'],
    delta={'reference': df_indicator.loc['plan', 'umsatz_ytd']},
    domain={'row': 0, 'column': 0}
))

fig_ind_profit_alt = go.Figure(go.Indicator(
    title="Gewinn Plan/Ist 2021 YTD",
    mode="number+delta",
    value=df_indicator.loc['ist', 'gewinn_ytd'],
    delta={'reference': df_indicator.loc['plan', 'gewinn_ytd']},
    domain={'row': 0, 'column': 1}
))

fig_ind_profit_alt.add_trace(go.Scatter(
    y=df_ind_scatter['gewinn_ytd'],
    x=df_ind_scatter['row_month']
))


fig_ind_margin.add_trace(go.Indicator(
    title="Deckungsbeitrag Plan/Ist 2021 YTD",
    mode="number+delta",
    value=df_indicator.loc['ist', 'db_ytd'],
    delta={'reference': df_indicator.loc['plan', 'db_ytd']},
    domain={'row': 0, 'column': 2}
))

########################################
# Figure Definition
fig_line = px.line(df_sql_data, x='row_year', y='umsatz',
                   color='forecast', labels=labels,
                   title='Umsatz Plan/Ist')

fig_bar = px.bar(df_sql_data, x="row_year", y="deckungsbeitrag",
                 color="forecast", barmode="group", labels=labels,
                 title="Deckungsbeitrag Plan/Ist")

fig_prd_grp_quantity = px.bar(df_prd_grp_quantity, x="Descr", y="Sum QTY",
                              color="syear", barmode="group", labels=labels,
                              title="Menge pro Produkt")

fig_cust_prog = px.pie(df_cust_prog, values='Count',
                       names='CustomerProg', title='Teilnahme Kundenbindungsprogramm')

fig_newsletter = px.pie(df_newsletter, values='Count',
                        names='Newsletter', title='Newsletter abonniert')

fig_sales_qty = px.bar(df_sales_qty, x="smonth",
                       y="Sum QTY", color="syear", barmode="group", labels=labels,
                       title="Menge pro Kunde")

########################################
# The Data App
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(
            html.H1("Daten einfach verfügbar", className="display-1")
        )),
        dbc.Row(dbc.Col(html.Hr())),
        dbc.Row([dbc.Col([
            html.P(
                "Daten nutzen, um bessere Entscheidungen schneller zu treffen.", className="lead"),
            html.Hr(),
            html.P("Historisch gewachsene SQL Datenbanken, diverse Cloud und SaaS Lösungen und dann gibt es da noch eine Reihe von Excel Dateien? Wieviel Zeit investieren Sie, um die relevanten Daten zu finden, aufzubereiten und für wichtige Entscheidungen zu analysieren?"),
            dbc.Button("Termin vereinbaren",
                       href="mailto:kontakt@pschwan.de",
                       color="danger", block=True),
            dbc.Button("Was ist ein Data Product?",
                       href="https://www.pschwan.de/digitalisierung/was-ist-das-ein-data-product", target="_blank", color="secondary", outline=True, block=True),
            dbc.Button("Download Data-driven Business Model",
                       href="https://pschwan.de/blog/uploads/Data-driven%20Business%20Model.pdf", target="_blank", color="secondary", outline=True, block=True),
        ]), dbc.Col(
            dbc.Alert(
                dcc.Markdown('''
             #### Das Demo Tech Stack
             - **MySQL** Datenbank, in meiner Infrastruktur
             - **Python**, Pandas, Requests und ein paar weitere Packages (GitHub Repo für CI/CD)
             - **FastAPI** = API Data Layer, um Daten und Dashboard zu verbinden (serverless in der Cloud)
             - **Plotly Dash** = Dashboard und Data App Funktionen (Cloud PaaS)

             Anm.: Es geht um die Daten und Anbindung, nicht um Information Design und UX. Für das Dashboard werden größtenteils Bootstrap Komponenten eingesetzt.
             
             '''), color="secondary"
            )
        )
        ]),
        dbc.Row(dbc.Col(html.Hr()), style=ma_top),
        dbc.Row([
            dbc.Col(html.H2("KPI Indikatoren - den aktuellen Status prüfen",
                            className="display-4")),
            dbc.Col(dbc.Alert(dcc.Markdown('''
                    #### keine Zeit?
                    - High-Level Indikatoren, um aggregierte KPIs zu visualisieren
                    - Kombiniere Zahl, Delta, Grafik und Chart
                    '''), color="secondary"))
        ]),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id='indicators_rev',
                        figure=fig_ind_rev
                    )
                ),
                dbc.Col(
                    dcc.Graph(
                        id='indicators_profit',
                        figure=fig_ind_profit
                    )
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id='indicators_rev_other',
                        figure=fig_ind_rev_alt
                    )
                ),
                dbc.Col(
                    dcc.Graph(
                        id='indicators_profit_other',
                        figure=fig_ind_profit_alt
                    )
                ),
            ]
        ),
        dbc.Row(dbc.Col(html.Hr())),
        dbc.Row([
            dbc.Col(html.H2("Einfach KPI Charts - Zusammenhänge und Beziehungen schnell erfassen",
                            className="display-4")),
            dbc.Col(dbc.Alert(dcc.Markdown('''
                    #### Es ist interaktiv - probiere es aus:
                    - Die Slider anpassen und die **Jahre auswählen**
                    - Die Maus über die Graphen bewegen und die **out-of-the-box Features** kennenlernen
                    - Zum Beispiel: Zoomen oder die Charts als Grafik speichern!
                    '''), color="danger"))
        ]),
        dbc.Row(
            [
                dbc.Col([
                    dcc.Graph(
                        id='umsatz_bar',
                        figure=fig_bar
                    ),
                    dcc.RangeSlider(
                        id='year_umsatz_bar',
                        min=df_sql_data['year'].min(),
                        max=df_sql_data['year'].max(),
                        value=[df_sql_data['year'].min(
                        ), df_sql_data['year'].max()],
                        marks={str(year): str(year)
                               for year in df_sql_data['year'].unique()},
                        step=None
                    )
                ]),
                dbc.Col([
                    dcc.Graph(
                        id='umsatz_line',
                        figure=fig_line
                    ),
                    dcc.RangeSlider(
                        id='year_umsatz_line',
                        min=df_sql_data['year'].min(),
                        max=df_sql_data['year'].max(),
                        value=[df_sql_data['year'].min(
                        ), df_sql_data['year'].max()],
                        marks={str(year): str(year)
                               for year in df_sql_data['year'].unique()},
                        step=None
                    )
                ])
            ]
        ),
        dbc.Row(dbc.Col(html.Hr()), style=ma_top),
        dbc.Jumbotron(
            [
                html.H1("Danke, wir benutzen Excel!", className="display-3"),
                html.P(
                    "Daten unterschiedlichster Quellen zur Verfügung stellen, integrieren und nutzen - auch in Excel.",
                    className="lead",
                ),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([
                        dcc.Markdown('''
                            #### IT Unterstützung, die zu Ihren Herausforderungen passt:
                            - Wo entstehen die täglichen Herausforderungen?
                            - Welche Daten und Informationen wären für die Problemlösung nützlich?
                            - Sind diese Daten verfügbar? Warum nicht?
                            - "Wir haben keine interne IT..."
                            '''),
                    ]),
                    dbc.Col([
                        dbc.Button("Termin vereinbaren",
                                   href="mailto:kontakt@pschwan.de",
                                   color="danger", block=True),
                        dbc.Button("Was ist ein Data Product?",
                                   href="https://www.pschwan.de/digitalisierung/was-ist-das-ein-data-product", target="_blank", color="secondary", outline=True, block=True),
                        dbc.Button("Download Data-driven Business Model",
                                   href="https://pschwan.de/blog/uploads/Data-driven%20Business%20Model.pdf", target="_blank", color="secondary", outline=True, block=True),
                    ]),
                ]),
            ],
            style=jumbo_style
        ),
        dbc.Row(dbc.Col(html.Hr()), style=ma_top),
        dbc.Row([
            dbc.Col(
                html.H2("Detaillierte Übersichten - Zusammenhänge identifizieren",
                        className="display-4")
            ),
            dbc.Col(dbc.Alert(dcc.Markdown('''
                    #### Überblick behalten:
                    - Details strukturieren, z.B.: in Tabs
                    - Selektieren und Aggregieren der Informationen durch Slider und Drop-Downs
                    - Ja, man könnte die Tabelle per "Download" in Excel weiter nutzen
                    '''), color="secondary"))
        ]),
        dbc.Tabs([
            dbc.Tab(dbc.Card(
                dbc.CardBody(
                    [
                        dcc.RangeSlider(
                            id='year_prd_qty',
                            min=df_prd_grp_quantity['Year'].min(),
                            max=df_prd_grp_quantity['Year'].max(),
                            value=[df_prd_grp_quantity['Year'].max(
                            ) - 1, df_prd_grp_quantity['Year'].max()],
                            marks={str(year): str(year)
                                   for year in df_prd_grp_quantity['Year'].unique()},
                            step=None
                        ),
                        dcc.Dropdown(
                            id='dd_prd_qty',
                            options=[{'label': k, 'value': k}
                                     for k in df_prd_grp_quantity['Product Group'].unique()],
                            value=['Pizza'],
                            multi=True,
                            placeholder='Alle Produkte - selektiere eine Produktgruppe'
                        ),
                        dcc.Graph(
                            id='fig_prd_grp_quantity',
                            figure=fig_prd_grp_quantity
                        ),

                        html.H3("2021 YTD KPIs",
                                className="display-4", style=ma_top),
                        dbc.Table.from_dataframe(
                            df_prd_grp_kpi, striped=True, bordered=True, hover=True, size="sm")
                    ]
                ),
                className="mt-3",
            ), label="Übersicht Produkte"),


            # zweiter Tab
            dbc.Tab(dbc.Card(
                dbc.CardBody([
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(dcc.Graph(
                                    id='fig_cust_prog',
                                    figure=fig_cust_prog
                                ), body=True, className="mt-3"), width=6
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dcc.Graph(
                                        id='fig_newsletter',
                                        figure=fig_newsletter
                                    ), body=True, className="mt-3"), width=6
                            ),
                        ]
                    ),
                    html.Hr(),
                    html.H3("Programm Kundenbindung KPIs",
                            className="display-4"),
                    dbc.Row([
                        dbc.Col([
                            html.P("Filter Programm Kundenbindung ja/nein"),
                            dcc.Dropdown(
                                id='dd_cust_prog',
                                options=[{'label': 'ja', 'value': 1},
                                         {'label': 'nein', 'value': 0}],
                                value=[1, 0],
                                multi=True,
                                placeholder='Alle angezeigt - selektiere ja/nein'
                            )
                        ]),
                        dbc.Col([
                            html.P("Filter Newsletter ja/nein"),
                            dcc.Dropdown(
                                id='dd_newsl',
                                options=[{'label': 'ja', 'value': 1},
                                         {'label': 'nein', 'value': 0}],
                                value=[1, 0],
                                multi=True,
                                placeholder='Alle angezeigt - selektiere ja/nein'
                            )
                        ])
                    ]),
                    dbc.Row(dbc.Col(html.Br())),
                    dbc.Row([
                        dbc.Col(
                            dcc.Graph(
                                id='fig_sales_qty',
                                figure=fig_sales_qty)),
                    ]
                    ),
                    html.Hr(),
                    html.H3("YTD 2021 KPIs", className="display-4"),
                    dbc.Table.from_dataframe(
                        df_sales_cust, id='tbl_cust_ytd', striped=True, bordered=True, hover=True, size="sm")
                ])
            ), label="Übersicht Kunden")
        ]),
        dbc.Jumbotron(
            [
                html.H1("IT Know-How as a Service", className="display-3"),
                html.P(
                    "IT Projekte erfolgreich umsetzen",
                    className="lead",
                ),
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([
                        dcc.Markdown('''
                            #### IT Unterstützung für Ihre Projekte und täglichen Herausforderungen:
                            - Sie benötigen IT Unterstützung?
                            - Sie **wissen gar nicht genau wobei** und haben kein Projekt?
                            - Sie können den Projektumfang nicht abschätzen?
                            - Die **Herausforderungen entstehen in der täglichen Arbeit**?
                            '''),
                    ]),
                    dbc.Col([
                        dbc.Button("Termin vereinbaren",
                                   href="mailto:kontakt@pschwan.de",
                                   color="danger", block=True),
                        dbc.Button("IT Know-How as a Service - mehr erfahren",
                                   href="https://www.pschwan.de/it-know-how-und-projekte-as-a-service", target="_blank", color="secondary", outline=True, block=True),
                        dbc.Button("Was ist ein Data Product?",
                                   href="https://www.pschwan.de/digitalisierung/was-ist-das-ein-data-product", target="_blank", color="secondary", outline=True, block=True),
                    ]),
                ]),
            ],
            style=jumbo_style
        ),
    ]
)

########################################
# Callbacks für DropDowns und Filter


@app.callback(
    Output('umsatz_bar', 'figure'),
    Input('year_umsatz_bar', 'value'))
def update_figure(selected_year):
    filtered_df = df_sql_data[(df_sql_data.year >= selected_year[0]) & (
        df_sql_data.year <= selected_year[1])]

    fig_bar = px.bar(filtered_df, x="row_year", y="deckungsbeitrag",
                     color="forecast", barmode="group", labels=labels,
                     title="Deckungsbeitrag Plan/Ist")

    fig_bar.update_layout(transition_duration=500)

    return fig_bar


@app.callback(
    Output('umsatz_line', 'figure'),
    Input('year_umsatz_line', 'value'))
def update_figure(selected_year):
    filtered_df = df_sql_data[(df_sql_data.year >= selected_year[0]) & (
        df_sql_data.year <= selected_year[1])]

    fig_line = px.line(filtered_df, x='row_year', y='umsatz',
                       color='forecast', labels=labels,
                       title='Umsatz Plan/Ist')

    fig_line.update_layout(transition_duration=500)

    return fig_line


# Dropdown
@app.callback(
    Output('fig_prd_grp_quantity', 'figure'),
    Input('dd_prd_qty', 'value'),
    Input('year_prd_qty', 'value')
)
def update_output(value, selected_year):
    filtered_df = df_prd_grp_quantity[(df_prd_grp_quantity.Year >= selected_year[0]) & (
        df_prd_grp_quantity.Year <= selected_year[1])]

    # wenn kein Wert in DropDown ausgewählt oder alle gelöscht
    if len(value) > 0:
        filter_df_prd_grp_qty = filtered_df[filtered_df['Product Group'].isin(
            value)]
    else:
        filter_df_prd_grp_qty = filtered_df

    fig_prd_grp_quantity = px.bar(filter_df_prd_grp_qty, x="Descr", y="Sum QTY",
                                  color="syear", barmode="group", labels=labels,
                                  title="Menge pro Produkt")

    return fig_prd_grp_quantity


@app.callback(
    Output('fig_sales_qty', 'figure'),
    Input('dd_cust_prog', 'value'),
    Input('dd_newsl', 'value')
)
def update_data(cust, news):
    # falls nichts ausgewählt, Default Werte
    if len(cust) == 0:
        cust = [0, 1]
    if len(news) == 0:
        news = [0, 1]

    filtered_df = df_sales_qty[(df_sales_qty['Customer Program'].isin(
        cust)) & (df_sales_qty['Newsletter'].isin(news))]

    fig_sales_qty = px.bar(filtered_df, x="smonth",
                           y="Sum QTY", color="syear", barmode="group", labels=labels,
                           title="Menge pro Kunde")

    return fig_sales_qty


########################################
# Server
if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)
