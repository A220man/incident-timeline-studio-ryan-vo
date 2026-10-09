from backend.app.services.evaluation import benchmark, scenario, score


def test_heldout_seeds_are_disjoint_and_deterministic():
    first=benchmark(17,3);second=benchmark(17,3)
    assert first==second
    training=set(first['training'][0]['result']['seeds'])
    assert training.isdisjoint(first['heldout']['seeds'])
    assert first['heldout']['tp']+first['heldout']['fn']>0
    assert first['baseline']['recall']==0 and first['baseline']['fp']==0
    assert first['heldout']['examples']


def test_pair_count_and_false_positive_accounting():
    events,labels=scenario(19)
    result=score(events,labels,600)
    assert sum(result[k] for k in ['tp','fp','fn','tn'])==len(events)*(len(events)-1)//2
    assert result['fp']>0 and result['tp']>0
