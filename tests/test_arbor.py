from arbor import Arbor


def test_strahler(simple_arbor: Arbor):
    strahler = simple_arbor.strahler
    assert strahler[1] == 2
    assert strahler[max(strahler)] == 1


def test_reroot(simple_arbor: Arbor):
    rerooted = simple_arbor.reroot(4)
    assert rerooted.leaves == {1, 5, 6}
    assert rerooted.root == 4


def test_subarbor(simple_arbor: Arbor):
    sub = simple_arbor.copy_below(3)
    assert set(sub.node_loc) == {3, 4, 6}
    sub._validate()


def test_cuts(simple_arbor: Arbor):
    cut = list(simple_arbor.cut(2, 3))
    assert len(cut) == 3
    for arb in cut:
        arb._validate()
    assert cut[0].root == 2
    assert sorted(cut[0].node_loc) == [2, 5]
    assert cut[1].root == 3
    assert sorted(cut[1].node_loc) == [3, 4, 6]
    assert cut[2].root == simple_arbor.root
    assert sorted(cut[2].node_loc) == [1]
