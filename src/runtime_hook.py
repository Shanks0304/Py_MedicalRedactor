import os
import sys
import multiprocessing

def init_multiprocessing():
    """Initialize multiprocessing to prevent reopening"""
    if sys.platform == 'darwin':
        os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
        multiprocessing.set_start_method('fork', force=True)
    
    # Create and immediately close a pool to initialize resources
    with multiprocessing.Pool(1) as pool:
        pool.apply(lambda: None)

if getattr(sys, 'frozen', False):
    multiprocessing.freeze_support()
    init_multiprocessing()
    
    os.environ['PYTHONPATH'] = sys._MEIPASS
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'