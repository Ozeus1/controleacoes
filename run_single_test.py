import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_relatorio_detalhes import TestRelatorioDetalhes
import unittest

# Create a test suite with only the failing test
suite = unittest.TestSuite()
suite.addTest(TestRelatorioDetalhes('test_historico_completo'))

# Run with verbose output
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Print detailed failure info
if result.failures:
    print("\n" + "="*80)
    print("DETAILED FAILURE INFORMATION:")
    print("="*80)
    for test, traceback in result.failures:
        print(traceback)
