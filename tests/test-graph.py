import nose

from runner.lib.config import TaskConfig
from runner.lib.graph import (
    TaskGraph,
    DependencyDoesNotExistError,
    CycleError
)


def test_graph_ok_single_deps():
    ok = [('apples', []), ('final', ['bees']), ('bees', ['birds']),
          ('oranges', ['apples']), ('birds', ['oranges'])]
    graph = TaskGraph(map(TaskConfig.fromtuple, ok))
    task_order = graph.sequential_ordering()
    assert task_order == ['apples', 'oranges', 'birds', 'bees', 'final']


def test_graph_ok_multi_deps():
    ok = [('cleanup', ['update_shared_repos']),
          ('clobber', ['checkout_tools']), ('check_ami', []),
          ('check_slavealloc', []),
          ('killprocs', ['update_shared_repos']),
          ('checkout_tools', ['check_ami', 'check_slavealloc']),
          ('purge_builds', ['clobber']),
          ('update_shared_repos', ['purge_builds']),
          ('buildbot', ['cleanup', 'killprocs']),
          ('done', ['buildbot'])]

    graph = TaskGraph(map(TaskConfig.fromtuple, ok))
    task_order = graph.sequential_ordering()

    #  We shouldn't test against a literal expected list here as there are
    #  a couple of parallelisable tasks.
    assert task_order.index('cleanup') > task_order.index('update_shared_repos')
    assert task_order[-1] == 'done'
    assert task_order.index('checkout_tools') > task_order.index('check_ami')
    assert task_order.index('checkout_tools') > task_order.index('check_slavealloc')
    assert task_order.index('buildbot') > task_order.index('cleanup')
    assert task_order.index('buildbot') > task_order.index('killprocs')


@nose.tools.raises(DependencyDoesNotExistError)
def test_graph_missing():
    missing_birds = [('apples', []), ('final', ['bees']), ('bees', ['birds']),
                     ('oranges', ['apples'])]
    TaskGraph(map(TaskConfig.fromtuple, missing_birds))


@nose.tools.raises(CycleError)
def test_graph_cycle():
    # extra dependency on orange causes a cycle
    cycle = [('apples', []), ('final', ['bees']), ('bees', ['birds']),
             ('oranges', ['apples', 'bees']), ('birds', ['oranges'])]
    graph = TaskGraph(map(TaskConfig.fromtuple, cycle))
    graph.sequential_ordering()
