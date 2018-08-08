def pytest_itemcollected(item):
    node = item.obj
    suf = node.__doc__ if node.__doc__ else node.__name__
    item._nodeid = '\n'.join(("\n", node.__name__.title(), '*' * len(node.__name__),  suf))