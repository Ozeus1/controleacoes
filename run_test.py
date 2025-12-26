import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_relatorio_detalhes import TestRelatorioDetalhes
import unittest

# Run all tests
suite = unittest.TestLoader().loadTestsFromTestCase(TestRelatorioDetalhes)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# Print summary
print("\n" + "="*80)
print("FINAL TEST SUMMARY")
print("="*80)
print(f"Tests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")
print(f"Success: {result.wasSuccessful()}")

if result.wasSuccessful():
    print("\n🎉 ALL TESTS PASSED! 🎉")
else:
    print("\n❌ Some tests failed")
    
    if result.failures:
        for test, traceback in result.failures:
            print("\n" + "="*80)
            print(f"FAILURE: {test}")
            print("="*80)
            print(traceback[:500])  # First 500 chars
