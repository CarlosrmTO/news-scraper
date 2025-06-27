"""
Test script to verify all competitor configurations are working correctly.
"""
import importlib
import pkgutil
import os
import sys
from pprint import pprint

def test_competitor_configs():
    """Test all competitor configurations."""
    # Add the current directory to the Python path
    sys.path.insert(0, os.path.abspath('.'))
    
    # Import the competitors package
    import competitors
    
    # Get all competitor configs
    all_competitors = competitors.get_all_competitors()
    
    if not all_competitors:
        print("❌ No competitor configurations found!")
        return False
    
    print(f"✅ Found {len(all_competitors)} competitor configurations")
    
    # Test each competitor
    success_count = 0
    for competitor in all_competitors:
        try:
            print(f"\n🔍 Testing {competitor['name']}:")
            
            # Check required fields
            required_fields = ['name', 'url', 'sitemap', 'is_own_site']
            for field in required_fields:
                if field not in competitor:
                    print(f"❌ Missing required field: {field}")
                    continue
                print(f"   - {field}: {competitor[field]}")
            
            # Test getting by name
            by_name = competitors.get_competitor_by_name(competitor['name'])
            if by_name and by_name['name'] == competitor['name']:
                print(f"   - ✅ Found by name")
            else:
                print(f"   - ❌ Not found by name")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error testing {competitor.get('name', 'unknown')}: {str(e)}")
    
    print(f"\n📊 Results: {success_count}/{len(all_competitors)} configurations tested successfully")
    return success_count == len(all_competitors)

if __name__ == "__main__":
    print("🚀 Starting competitor configuration tests...")
    if test_competitor_configs():
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)
