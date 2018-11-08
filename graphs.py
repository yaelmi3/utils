import plotly
from colorlover import scales
from collections import namedtuple, OrderedDict


def create_2_columns_table(headers, data, sort=True):
    """
    Sorts the dict data to match the table datastruct and sorting the data if required
    :type headers: list
    :type data: dict
    :type sort: bool
    :rtype: plotly.offline.plot
    """
    sorted_data = _sort_data(data) if sort else data
    align_len = len(sorted_data)
    values = [list(sorted_data.keys()),
              list(sorted_data.values())]
    return create_generic_table(headers, values, align_len)


def create_generic_table(headers, values, align_len):
    """
    Create a generic table using plotly. Values is a list of list that represents the cells
    :type headers: list
    :type values: list[list]
    :type align_len: ubt
    :rtype: plotly.offline.plot
    """
    height = 1000 if align_len > 100 else 500
    trace = plotly.graph_objs.Table(
        columnwidth=[300, 80],
        header=dict(values=headers,
                    line=dict(color='#7D7F80'),
                    fill=dict(color='#9ae59a'),
                    align=['left'] * align_len),
        cells=dict(values=values,
                   fill=dict(color='#e6ffe6'),
                   align=['left'] * align_len))
    layout = dict(width=1500, height=height)
    data = [trace]
    fig = dict(data=data, layout=layout)
    return plotly.offline.plot(fig, output_type='div')


def create_graph_bar(data, title='', sort=True):
    """
    Generate bars graph and return it as html text
    :type data: dict
    :type title: str
    :type sort: bool
    :rtype: str
    """
    plotly.offline.init_notebook_mode(connected=True)
    plot_bar_axes = _handle_plot_data(data, sort)
    data = {
        "data": [plotly.graph_objs.Bar(x=plot_bar_axes.x, y=plot_bar_axes.y)],
        "layout": plotly.graph_objs.Layout(title=title,
                                           xaxis={'tickangle': 45},
                                           autosize=True)
    }
    return plotly.offline.plot(data, output_type='div')


def create_pie_chart(labels, values):
    colors = scales[str(len(labels))]['seq']['YlGn']
    trace = plotly.graph_objs.Pie(labels=labels, values=values,
                                  hoverinfo='label+percent', textinfo='value',
                                  textfont=dict(size=12),
                                  marker=dict(colors=list(colors),
                                              line=dict(color='#000000', width=1)))
    return plotly.offline.plot([trace], output_type='div')


def _handle_plot_data(data, sort):
    """
    Adjusts the x/y data for bar chart
    :t data:
    :type sort: bool
    :rtype: PlotBarAxes
    """
    PlotBarAxes = namedtuple('PlotBarAxes', 'x y')
    quantity_data = data
    if sort:
        quantity_data = _sort_data(data)
    return PlotBarAxes(x=tuple(quantity_data.keys()), y=tuple(quantity_data.values()))


def _sort_data(data):
    return OrderedDict(sorted(data.items(), key=lambda t: t[1], reverse=True))