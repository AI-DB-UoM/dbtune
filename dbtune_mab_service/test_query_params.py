#!/usr/bin/env python3
"""
Test script to verify query parameters are correctly loaded from configuration.

Tests:
1. Verify queries_start parameter can be loaded
2. Verify batch_size parameter can be loaded
3. Verify offset parameter can be loaded
4. Test different configuration files
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config, get_tuning_config, ConfigLoader


def test_query_params_default():
    """Test 1: Load query parameters from default config"""
    print("\n[Test 1] Load query parameters from default config")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config()
        tuning_config = get_tuning_config()
        
        required_keys = ['queries_start', 'batch_size', 'offset']
        for key in required_keys:
            if key not in tuning_config:
                print(f"  ✗ Missing key: {key}")
                return False
        
        print(f"  ✓ All query parameters found:")
        print(f"    - queries_start: {tuning_config['queries_start']}")
        print(f"    - batch_size: {tuning_config['batch_size']}")
        print(f"    - offset: {tuning_config['offset']}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_query_params_dev():
    """Test 2: Load query parameters from dev config"""
    print("\n[Test 2] Load query parameters from config.yaml (dev)")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config('configs/config.yaml')
        tuning_config = get_tuning_config()
        
        if tuning_config['batch_size'] == 10:
            print(f"  ✓ Dev config loaded correctly:")
            print(f"    - queries_start: {tuning_config['queries_start']}")
            print(f"    - batch_size: {tuning_config['batch_size']}")
            print(f"    - offset: {tuning_config['offset']}")
            return True
        else:
            print(f"  ✗ Unexpected batch_size: {tuning_config['batch_size']}")
            return False
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_query_params_prod():
    """Test 3: Load query parameters from prod config"""
    print("\n[Test 3] Load query parameters from config.prod.yaml (prod)")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config('configs/config.prod.yaml')
        tuning_config = get_tuning_config()
        
        if tuning_config['batch_size'] == 20:
            print(f"  ✓ Prod config loaded correctly:")
            print(f"    - queries_start: {tuning_config['queries_start']}")
            print(f"    - batch_size: {tuning_config['batch_size']}")
            print(f"    - offset: {tuning_config['offset']}")
            return True
        else:
            print(f"  ✗ Unexpected batch_size: {tuning_config['batch_size']}")
            return False
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_query_params_test():
    """Test 4: Load query parameters from test config"""
    print("\n[Test 4] Load query parameters from config.test.yaml (test)")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config('configs/config.test.yaml')
        tuning_config = get_tuning_config()
        
        if tuning_config['batch_size'] == 5:
            print(f"  ✓ Test config loaded correctly:")
            print(f"    - queries_start: {tuning_config['queries_start']}")
            print(f"    - batch_size: {tuning_config['batch_size']}")
            print(f"    - offset: {tuning_config['offset']}")
            return True
        else:
            print(f"  ✗ Unexpected batch_size: {tuning_config['batch_size']}")
            return False
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_query_params_default_config():
    """Test 5: Load query parameters from config_default.yaml"""
    print("\n[Test 5] Load query parameters from config_default.yaml")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config('configs/config_default.yaml')
        tuning_config = get_tuning_config()
        
        if tuning_config['batch_size'] == 10:
            print(f"  ✓ Default config loaded correctly:")
            print(f"    - queries_start: {tuning_config['queries_start']}")
            print(f"    - batch_size: {tuning_config['batch_size']}")
            print(f"    - offset: {tuning_config['offset']}")
            return True
        else:
            print(f"  ✗ Unexpected batch_size: {tuning_config['batch_size']}")
            return False
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_all_tuning_params():
    """Test 6: Verify all tuning parameters are present"""
    print("\n[Test 6] Verify all tuning parameters are present")
    
    try:
        # Reset singleton
        ConfigLoader._instance = None
        ConfigLoader._config = None
        
        load_config()
        tuning_config = get_tuning_config()
        
        required_keys = [
            'hyp_check_rounds', 'rounds', 'super_static_context_size',
            'cluster_id_start', 'queries_start', 'batch_size', 'offset'
        ]
        
        missing_keys = [k for k in required_keys if k not in tuning_config]
        
        if missing_keys:
            print(f"  ✗ Missing keys: {missing_keys}")
            return False
        
        print(f"  ✓ All tuning parameters present:")
        for key in required_keys:
            print(f"    - {key}: {tuning_config[key]}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Query Parameters Configuration Tests")
    print("=" * 60)
    
    tests = [
        test_query_params_default,
        test_query_params_dev,
        test_query_params_prod,
        test_query_params_test,
        test_query_params_default_config,
        test_all_tuning_params,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! Query parameters are correctly configured.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
