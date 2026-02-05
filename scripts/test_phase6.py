#!/usr/bin/env python3
"""Manual test script for Phase 6 (Configuration Updates).

Run this script to verify the implementation without needing pytest.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from src.faqbot.config import Config


def print_test_header(test_name):
    """Print a test section header."""
    print(f"\n{'=' * 60}")
    print(f"  {test_name}")
    print(f"{'=' * 60}")


def print_success(message):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message):
    """Print error message."""
    print(f"❌ {message}")


def test_config_defaults():
    """Test configuration defaults for new fields."""
    print("\n1. Testing configuration defaults...")

    # Create config with minimal required fields
    config = Config(
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_allowed_channels=["C123"],
        anthropic_api_key="sk-ant-test",
        faq_source="markdown",
        faq_file_path="./faq.md",
    )

    # Check suggestion features defaults
    if config.reaction_search_enabled != True:
        print_error(f"reaction_search_enabled default wrong: {config.reaction_search_enabled}")
        return False

    if config.slash_command_enabled != True:
        print_error(f"slash_command_enabled default wrong: {config.slash_command_enabled}")
        return False

    if config.suggestion_min_similarity != 0.50:
        print_error(
            f"suggestion_min_similarity default wrong: {config.suggestion_min_similarity}"
        )
        return False

    if config.suggestion_top_k != 5:
        print_error(f"suggestion_top_k default wrong: {config.suggestion_top_k}")
        return False

    # Check status monitoring defaults
    if config.status_monitoring_enabled != True:
        print_error(f"status_monitoring_enabled default wrong: {config.status_monitoring_enabled}")
        return False

    if config.slack_status_channels != []:
        print_error(f"slack_status_channels default wrong: {config.slack_status_channels}")
        return False

    if config.status_cache_ttl_hours != 24:
        print_error(f"status_cache_ttl_hours default wrong: {config.status_cache_ttl_hours}")
        return False

    print_success("All configuration defaults are correct")
    return True


def test_config_custom_values():
    """Test configuration with custom values."""
    print("\n2. Testing configuration with custom values...")

    config = Config(
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_allowed_channels=["C123"],
        anthropic_api_key="sk-ant-test",
        faq_source="markdown",
        faq_file_path="./faq.md",
        reaction_search_enabled=False,
        slash_command_enabled=False,
        suggestion_min_similarity=0.60,
        suggestion_top_k=10,
        status_monitoring_enabled=False,
        slack_status_channels=["C_STATUS", "C_INCIDENTS"],
        status_cache_ttl_hours=48,
    )

    if config.reaction_search_enabled != False:
        print_error("reaction_search_enabled not set correctly")
        return False

    if config.slash_command_enabled != False:
        print_error("slash_command_enabled not set correctly")
        return False

    if config.suggestion_min_similarity != 0.60:
        print_error("suggestion_min_similarity not set correctly")
        return False

    if config.suggestion_top_k != 10:
        print_error("suggestion_top_k not set correctly")
        return False

    if config.status_monitoring_enabled != False:
        print_error("status_monitoring_enabled not set correctly")
        return False

    if config.slack_status_channels != ["C_STATUS", "C_INCIDENTS"]:
        print_error("slack_status_channels not set correctly")
        return False

    if config.status_cache_ttl_hours != 48:
        print_error("status_cache_ttl_hours not set correctly")
        return False

    print_success("Custom configuration values set correctly")
    return True


def test_validation_suggestion_min_similarity():
    """Test validation of suggestion_min_similarity."""
    print("\n3. Testing suggestion_min_similarity validation...")

    # Valid cases
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_min_similarity=0.50,
        )
        config.validate()
    except ValueError:
        print_error("Valid suggestion_min_similarity (0.50) rejected")
        return False

    # Invalid: too high
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_min_similarity=1.5,
        )
        config.validate()
        print_error("Invalid suggestion_min_similarity (1.5) not caught")
        return False
    except ValueError:
        pass  # Expected

    # Invalid: negative
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_min_similarity=-0.1,
        )
        config.validate()
        print_error("Invalid suggestion_min_similarity (-0.1) not caught")
        return False
    except ValueError:
        pass  # Expected

    print_success("suggestion_min_similarity validation works correctly")
    return True


def test_validation_suggestion_top_k():
    """Test validation of suggestion_top_k."""
    print("\n4. Testing suggestion_top_k validation...")

    # Valid case
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_top_k=5,
        )
        config.validate()
    except ValueError:
        print_error("Valid suggestion_top_k (5) rejected")
        return False

    # Invalid: zero
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_top_k=0,
        )
        config.validate()
        print_error("Invalid suggestion_top_k (0) not caught")
        return False
    except ValueError:
        pass  # Expected

    # Invalid: negative
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            suggestion_top_k=-1,
        )
        config.validate()
        print_error("Invalid suggestion_top_k (-1) not caught")
        return False
    except ValueError:
        pass  # Expected

    print_success("suggestion_top_k validation works correctly")
    return True


def test_validation_status_cache_ttl():
    """Test validation of status_cache_ttl_hours."""
    print("\n5. Testing status_cache_ttl_hours validation...")

    # Valid case
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            status_cache_ttl_hours=24,
        )
        config.validate()
    except ValueError:
        print_error("Valid status_cache_ttl_hours (24) rejected")
        return False

    # Invalid: zero
    try:
        config = Config(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            slack_allowed_channels=["C123"],
            anthropic_api_key="sk-ant-test",
            faq_source="markdown",
            faq_file_path="./faq.md",
            status_cache_ttl_hours=0,
        )
        config.validate()
        print_error("Invalid status_cache_ttl_hours (0) not caught")
        return False
    except ValueError:
        pass  # Expected

    print_success("status_cache_ttl_hours validation works correctly")
    return True


def test_parse_status_channels():
    """Test parsing of SLACK_STATUS_CHANNELS from env."""
    print("\n6. Testing parsing of status channels from environment...")

    # Save original env
    original_env = os.environ.copy()

    try:
        # Set up minimal required env vars
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
        os.environ["SLACK_APP_TOKEN"] = "xapp-test"
        os.environ["SLACK_ALLOWED_CHANNELS"] = "C123,C456"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["FAQ_SOURCE"] = "markdown"
        os.environ["FAQ_FILE_PATH"] = "./faq.md"

        # Test with multiple channels
        os.environ["SLACK_STATUS_CHANNELS"] = "C_STATUS,C_INCIDENTS,C_ALERTS"
        config = Config.from_env()

        if len(config.slack_status_channels) != 3:
            print_error(f"Expected 3 status channels, got {len(config.slack_status_channels)}")
            return False

        if config.slack_status_channels != ["C_STATUS", "C_INCIDENTS", "C_ALERTS"]:
            print_error(f"Status channels parsed incorrectly: {config.slack_status_channels}")
            return False

        # Test with empty string (no channels)
        os.environ["SLACK_STATUS_CHANNELS"] = ""
        config = Config.from_env()

        if len(config.slack_status_channels) != 0:
            print_error(f"Expected 0 status channels for empty string, got {len(config.slack_status_channels)}")
            return False

        # Test with no env var set
        if "SLACK_STATUS_CHANNELS" in os.environ:
            del os.environ["SLACK_STATUS_CHANNELS"]
        config = Config.from_env()

        if len(config.slack_status_channels) != 0:
            print_error(f"Expected 0 status channels when not set, got {len(config.slack_status_channels)}")
            return False

        print_success("Status channels parsing works correctly")
        return True

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_boolean_parsing():
    """Test parsing of boolean environment variables."""
    print("\n7. Testing boolean environment variable parsing...")

    original_env = os.environ.copy()

    try:
        # Set up minimal required env vars
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
        os.environ["SLACK_APP_TOKEN"] = "xapp-test"
        os.environ["SLACK_ALLOWED_CHANNELS"] = "C123"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        os.environ["FAQ_SOURCE"] = "markdown"
        os.environ["FAQ_FILE_PATH"] = "./faq.md"

        # Test "true" (lowercase)
        os.environ["REACTION_SEARCH_ENABLED"] = "true"
        os.environ["SLASH_COMMAND_ENABLED"] = "true"
        os.environ["STATUS_MONITORING_ENABLED"] = "true"
        config = Config.from_env()

        if not config.reaction_search_enabled:
            print_error("'true' not parsed correctly for reaction_search_enabled")
            return False

        # Test "false" (lowercase)
        os.environ["REACTION_SEARCH_ENABLED"] = "false"
        config = Config.from_env()

        if config.reaction_search_enabled:
            print_error("'false' not parsed correctly")
            return False

        # Test "True" (capitalized)
        os.environ["SLASH_COMMAND_ENABLED"] = "True"
        config = Config.from_env()

        if not config.slash_command_enabled:
            print_error("'True' not parsed correctly")
            return False

        # Test "FALSE" (uppercase)
        os.environ["STATUS_MONITORING_ENABLED"] = "FALSE"
        config = Config.from_env()

        if config.status_monitoring_enabled:
            print_error("'FALSE' not parsed correctly")
            return False

        print_success("Boolean environment variables parsed correctly")
        return True

    finally:
        os.environ.clear()
        os.environ.update(original_env)


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  TESTING PHASE 6: CONFIGURATION MODULE")
    print("=" * 60)

    tests = [
        test_config_defaults,
        test_config_custom_values,
        test_validation_suggestion_min_similarity,
        test_validation_suggestion_top_k,
        test_validation_status_cache_ttl,
        test_parse_status_channels,
        test_boolean_parsing,
    ]

    passed = 0
    failed = 0

    try:
        for test in tests:
            if test():
                passed += 1
            else:
                failed += 1

        print("\n" + "=" * 60)
        if failed == 0:
            print(f"  ✅ ALL {passed} TESTS PASSED!")
        else:
            print(f"  ⚠️  {passed} PASSED, {failed} FAILED")
        print("=" * 60)

        if failed == 0:
            print("\n✨ Phase 6 implementation verified!")
            print("   - Configuration module updated with new fields")
            print("   - Reaction search configuration added")
            print("   - Slash command configuration added")
            print("   - Status monitoring configuration added")
            print("   - Validation logic working correctly")
            print("   - Environment variable parsing tested")
            print("\nNext step: Phase 7 - Add metrics tracking")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Review implementation.")

        print("=" * 60 + "\n")

    except Exception as e:
        print("\n" + "=" * 60)
        print("  ❌ TEST FAILED WITH ERROR")
        print("=" * 60)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
