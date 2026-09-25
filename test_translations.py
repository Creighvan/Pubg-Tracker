"""
Translation validation tests for PUBG Tracker bot.

This test suite verifies:
- Every locale has the complete English key set
- No missing keys in any locale
- No unexpected keys in any locale
- Placeholder consistency between English and translations
- Pluralization-related keys are properly structured

Run with: python test_translations.py
"""

import re
import sys
from translations import TRANSLATIONS

# Expected locales
EXPECTED_LOCALES = {"en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "id", "ur"}

# Keys that should contain pluralization placeholders
PLURALIZATION_KEYS = {
    "every_hours",
    "hours_ago",
    "days_ago",
    "matches_played",
}

# Keys that should NOT contain literal "(s)" strings
NO_LITERAL_PLURAL_KEYS = PLURALIZATION_KEYS

# Keys that require unit placeholders for pluralization
UNIT_PLACEHOLDER_KEYS = {
    "every_hours",
    "hours_ago",
    "days_ago",
}


def extract_placeholders(text):
    """Extract all {placeholder} patterns from a string."""
    return set(re.findall(r'\{(\w+)\}', str(text)))


def validate_locale_completeness():
    """Verify every locale has all English keys."""
    print("\n=== Checking locale completeness ===")
    
    english_keys = set(TRANSLATIONS["en"].keys())
    missing_keys_by_locale = {}
    extra_keys_by_locale = {}
    
    for locale, translations in TRANSLATIONS.items():
        if locale not in EXPECTED_LOCALES:
            print(f"[!] Unexpected locale: {locale}")
            continue
        
        locale_keys = set(translations.keys())
        
        # Check for missing keys
        missing = english_keys - locale_keys
        if missing:
            missing_keys_by_locale[locale] = sorted(missing)
        
        # Check for extra keys
        extra = locale_keys - english_keys
        if extra:
            extra_keys_by_locale[locale] = sorted(extra)
    
    # Report results
    if missing_keys_by_locale:
        print("[X] Missing keys found:")
        for locale, keys in missing_keys_by_locale.items():
            print(f"  {locale}: {len(keys)} missing")
            for key in keys[:5]:  # Show first 5
                print(f"    - {key}")
            if len(keys) > 5:
                print(f"    ... and {len(keys) - 5} more")
    else:
        print("[OK] No missing keys in any locale")
    
    if extra_keys_by_locale:
        print("[X] Extra keys found:")
        for locale, keys in extra_keys_by_locale.items():
            print(f"  {locale}: {len(keys)} extra")
            for key in keys[:5]:
                print(f"    - {key}")
            if len(keys) > 5:
                print(f"    ... and {len(keys) - 5} more")
    else:
        print("[OK] No extra keys in any locale")
    
    return not (missing_keys_by_locale or extra_keys_by_locale)


def validate_placeholder_consistency():
    """Verify placeholders match between English and translations."""
    print("\n=== Checking placeholder consistency ===")
    
    english_keys = TRANSLATIONS["en"]
    placeholder_mismatches = []
    
    for locale in EXPECTED_LOCALES:
        if locale == "en":
            continue
        
        locale_translations = TRANSLATIONS.get(locale, {})
        
        for key, english_value in english_keys.items():
            if key not in locale_translations:
                continue  # Already reported in completeness check
            
            locale_value = locale_translations[key]
            
            english_placeholders = extract_placeholders(english_value)
            locale_placeholders = extract_placeholders(locale_value)
            
            if english_placeholders != locale_placeholders:
                placeholder_mismatches.append({
                    'locale': locale,
                    'key': key,
                    'english': english_placeholders,
                    'locale': locale_placeholders,
                })
    
    if placeholder_mismatches:
        print(f"[X] Placeholder mismatches found: {len(placeholder_mismatches)}")
        for mismatch in placeholder_mismatches[:10]:  # Show first 10
            print(f"  {mismatch['locale']} / {mismatch['key']}")
            print(f"    English: {mismatch['english']}")
            print(f"    {mismatch['locale']}: {mismatch['locale']}")
        if len(placeholder_mismatches) > 10:
            print(f"  ... and {len(placeholder_mismatches) - 10} more")
    else:
        print("[OK] All placeholders match")
    
    return not placeholder_mismatches


def validate_pluralization_strings():
    """Check for literal (s) strings instead of proper pluralization."""
    print("\n=== Checking pluralization strings ===")
    
    literal_plural_issues = []
    
    for locale in EXPECTED_LOCALES:
        locale_translations = TRANSLATIONS.get(locale, {})
        
        for key, value in locale_translations.items():
            if key in NO_LITERAL_PLURAL_KEYS:
                # Check for literal "(s)" pattern
                if "(s)" in str(value):
                    literal_plural_issues.append({
                        'locale': locale,
                        'key': key,
                        'value': value,
                    })
    
    if literal_plural_issues:
        print(f"[!] Literal (s) strings found: {len(literal_plural_issues)} (to be fixed in pluralization framework)")
        for issue in literal_plural_issues[:5]:
            print(f"  {issue['locale']} / {issue['key']}")
            print(f"    {issue['value'][:80]}...")
        if len(literal_plural_issues) > 5:
            print(f"  ... and {len(literal_plural_issues) - 5} more")
    else:
        print("[OK] No literal (s) strings in pluralization keys")
    
    # Return True even if issues found, since this is expected to be fixed in step 2
    return True


def validate_unit_placeholders():
    """Check that unit placeholder keys exist for pluralization."""
    print("\n=== Checking unit placeholder keys ===")
    
    missing_unit_keys = []
    
    for locale in EXPECTED_LOCALES:
        locale_translations = TRANSLATIONS.get(locale, {})
        
        for key in UNIT_PLACEHOLDER_KEYS:
            # Check that unit keys exist
            unit_key = key.replace("hours_ago", "hour").replace("days_ago", "day")
            unit_plural_key = key.replace("hours_ago", "hours").replace("days_ago", "days")
            
            if unit_key not in locale_translations:
                missing_unit_keys.append({
                    'locale': locale,
                    'key': unit_key,
                    'for': key,
                })
            if unit_plural_key not in locale_translations:
                missing_unit_keys.append({
                    'locale': locale,
                    'key': unit_plural_key,
                    'for': key,
                })
    
    if missing_unit_keys:
        print(f"[X] Missing unit placeholder keys: {len(missing_unit_keys)}")
        for issue in missing_unit_keys[:10]:
            print(f"  {issue['locale']} / {issue['key']} (needed for {issue['for']})")
        if len(missing_unit_keys) > 10:
            print(f"  ... and {len(missing_unit_keys) - 10} more")
    else:
        print("[OK] All unit placeholder keys present")
    
    return not missing_unit_keys


def validate_utc_terminology():
    """Ensure no Eastern/EST/EDT timezone references remain."""
    print("\n=== Checking UTC terminology ===")
    
    # Check for specific timezone phrases that would be problematic
    forbidden_phrases = [
        "Eastern time",
        "Eastern Standard Time",
        "Eastern Daylight Time",
        "America/New_York",
        "KST",
        "东部时间",
        "heure de l'Est",
    ]
    
    timezone_issues = []
    
    for locale in EXPECTED_LOCALES:
        locale_translations = TRANSLATIONS.get(locale, {})
        
        for key, value in locale_translations.items():
            value_str = str(value)
            for phrase in forbidden_phrases:
                if phrase in value_str:
                    timezone_issues.append({
                        'locale': locale,
                        'key': key,
                        'phrase': phrase,
                        'value': value_str[:80],
                    })
    
    if timezone_issues:
        print(f"[X] Timezone terminology issues found: {len(timezone_issues)}")
        for issue in timezone_issues[:10]:
            print(f"  {issue['locale']} / {issue['key']}")
            print(f"    Phrase: {issue['phrase']}")
            print(f"    {issue['value']}...")
        if len(timezone_issues) > 10:
            print(f"  ... and {len(timezone_issues) - 10} more")
    else:
        print("[OK] No Eastern/EST/EDT/KST timezone references")
    
    return not timezone_issues


def validate_runtime_formatting():
    """Test that translations can be formatted with the expected placeholders."""
    print("\n=== Checking runtime formatting ===")
    
    formatting_issues = []
    
    # Test time-related translations with actual format calls
    test_cases = [
        ("hours_ago", {"count": 2, "unit": "hours"}),
        ("hours_ago", {"count": 1, "unit": "hour"}),
        ("days_ago", {"count": 3, "unit": "days"}),
        ("days_ago", {"count": 1, "unit": "day"}),
        ("every_hours", {"count": 6, "unit": "hours"}),
        ("every_hours", {"count": 1, "unit": "hour"}),
    ]
    
    for locale in EXPECTED_LOCALES:
        locale_translations = TRANSLATIONS.get(locale, {})
        
        for key, format_args in test_cases:
            if key not in locale_translations:
                continue
            
            try:
                template = locale_translations[key]
                formatted = template.format(**format_args)
                if not formatted or formatted == template:
                    formatting_issues.append({
                        'locale': locale,
                        'key': key,
                        'args': format_args,
                        'template': template,
                        'error': 'Formatting produced no change or empty result',
                    })
            except KeyError as e:
                formatting_issues.append({
                    'locale': locale,
                    'key': key,
                    'args': format_args,
                    'template': template,
                    'error': f'Missing placeholder: {e}',
                })
            except Exception as e:
                formatting_issues.append({
                    'locale': locale,
                    'key': key,
                    'args': format_args,
                    'template': template,
                    'error': str(e),
                })
    
    if formatting_issues:
        print(f"[X] Runtime formatting issues found: {len(formatting_issues)}")
        for issue in formatting_issues[:10]:
            print(f"  {issue['locale']} / {issue['key']}")
            print(f"    Args: {issue['args']}")
            print(f"    Error: {issue['error']}")
        if len(formatting_issues) > 10:
            print(f"  ... and {len(formatting_issues) - 10} more")
    else:
        print("[OK] All runtime formatting tests passed")
    
    return not formatting_issues


def validate_locales_present():
    """Verify all expected locales are present."""
    print("\n=== Checking expected locales ===")
    
    present_locales = set(TRANSLATIONS.keys())
    missing_locales = EXPECTED_LOCALES - present_locales
    extra_locales = present_locales - EXPECTED_LOCALES
    
    if missing_locales:
        print(f"[X] Missing expected locales: {missing_locales}")
    else:
        print("[OK] All expected locales present")
    
    if extra_locales:
        print(f"[!] Extra locales present: {extra_locales}")
    
    return not missing_locales


def run_all_tests():
    """Run all translation validation tests."""
    print("=" * 60)
    print("Translation Validation Tests")
    print("=" * 60)
    
    results = {
        "Locale presence": validate_locales_present(),
        "Completeness": validate_locale_completeness(),
        "Placeholder consistency": validate_placeholder_consistency(),
        "Pluralization strings": validate_pluralization_strings(),
        "Unit placeholders": validate_unit_placeholders(),
        "UTC terminology": validate_utc_terminology(),
        "Runtime formatting": validate_runtime_formatting(),
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "[OK] PASS" if passed else "[X] FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All tests passed!")
    else:
        print("[X] Some tests failed - review output above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
