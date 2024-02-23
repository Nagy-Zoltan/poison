import poison

print('hello')

import pickle

poison.poison('print', 'abs', 'X')



def foo():
    if True:
        import re
    import os
    print('hello')
