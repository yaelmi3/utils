from collections import namedtuple, OrderedDict

import plotly


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
        "layout": plotly.graph_objs.Layout(title=title, margin={'b': 150}, xaxis={'tickangle': 45},
                                           autosize=True, width=1500, height=700)
    }
    return plotly.offline.plot(data, output_type='div')


def _handle_plot_data(data, sort):
    PlotBarAxes = namedtuple('PlotBarAxes', 'x y')
    quantity_data = {key_name: len(members) for key_name, members in data.items()}
    if sort:
        quantity_data = OrderedDict(sorted(quantity_data.items(), key=lambda t: t[1], reverse=True))
    return PlotBarAxes(x=tuple(quantity_data.keys()), y=tuple(quantity_data.values()))
