<<<<<<< HEAD
from pygbe.main import main

def test_lysozyme():
    res = main(['', '../examples/lys', return_output_dict=True])

=======
import os
import pickle
import pytest
import functools

try:
    import pycuda
except ImportError:
    ans = input('PyCUDA not found.  Regression tests will take forever.  Do you want to continue? [y/n] ')
    if ans in ['Y', 'y']:
        pass
    else:
        sys.exit()

from pygbe.main import main

@pytest.mark.parametrize('key', ['total_elements',
                                 'E_solv_kJ',
                                 'E_coul_kcal',
                                 'E_coul_kJ',
                                 'E_solv_kcal'])
def test_lysozyme(key):
    results = get_results()

    with open('lysozyme.pickle', 'rb') as f:
        base_results = pickle.load(f)

    assert base_results[key] == results[key]

@functools.lru_cache(5)
def get_results():
    print('Generating results for lysozyme example...')
    if os.getcwd().rsplit('/', 1)[1] == 'tests':
        results = main(['','../examples/lys'],
                        log_output=False,
                        return_results_dict=True)
    elif os.getcwd().rsplit('/', 1)[1] == 'pygbe':
        results = main(['','./examples/lys'],
                        log_output=False,
                        return_results_dict=True)
    else:
        print("Run tests from either the main repo directory or the tests directory")

    return results
>>>>>>> py3port
