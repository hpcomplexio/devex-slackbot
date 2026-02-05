#!/usr/bin/env python3
"""Manual test script for Phase 7 (Metrics Tracking).

Run this script to verify the implementation without needing pytest.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.faqbot.state.metrics import BotMetrics


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


def test_metrics_initialization():
    """Test metrics object initialization."""
    print("\n1. Testing metrics initialization...")

    metrics = BotMetrics()

    # Check existing fields
    if metrics.questions_detected != 0:
        print_error(f"questions_detected should be 0, got {metrics.questions_detected}")
        return False

    # Check new fields
    if metrics.reaction_searches != 0:
        print_error(f"reaction_searches should be 0, got {metrics.reaction_searches}")
        return False

    if metrics.slash_commands != 0:
        print_error(f"slash_commands should be 0, got {metrics.slash_commands}")
        return False

    if metrics.suggestions_shown != 0:
        print_error(f"suggestions_shown should be 0, got {metrics.suggestions_shown}")
        return False

    if metrics.suggestions_clicked != 0:
        print_error(f"suggestions_clicked should be 0, got {metrics.suggestions_clicked}")
        return False

    if metrics.status_updates_cached != 0:
        print_error(f"status_updates_cached should be 0, got {metrics.status_updates_cached}")
        return False

    if metrics.status_correlations_shown != 0:
        print_error(
            f"status_correlations_shown should be 0, got {metrics.status_correlations_shown}"
        )
        return False

    print_success("All metrics initialized to 0")
    return True


def test_increment_reaction_searches():
    """Test reaction_searches counter."""
    print("\n2. Testing reaction_searches increment...")

    metrics = BotMetrics()

    metrics.increment_reaction_searches()
    if metrics.reaction_searches != 1:
        print_error(f"Expected 1, got {metrics.reaction_searches}")
        return False

    metrics.increment_reaction_searches()
    metrics.increment_reaction_searches()
    if metrics.reaction_searches != 3:
        print_error(f"Expected 3, got {metrics.reaction_searches}")
        return False

    print_success("reaction_searches counter increments correctly")
    return True


def test_increment_slash_commands():
    """Test slash_commands counter."""
    print("\n3. Testing slash_commands increment...")

    metrics = BotMetrics()

    metrics.increment_slash_commands()
    if metrics.slash_commands != 1:
        print_error(f"Expected 1, got {metrics.slash_commands}")
        return False

    metrics.increment_slash_commands()
    if metrics.slash_commands != 2:
        print_error(f"Expected 2, got {metrics.slash_commands}")
        return False

    print_success("slash_commands counter increments correctly")
    return True


def test_increment_suggestions_shown():
    """Test suggestions_shown counter."""
    print("\n4. Testing suggestions_shown increment...")

    metrics = BotMetrics()

    metrics.increment_suggestions_shown(5)
    if metrics.suggestions_shown != 5:
        print_error(f"Expected 5, got {metrics.suggestions_shown}")
        return False

    metrics.increment_suggestions_shown(3)
    if metrics.suggestions_shown != 8:
        print_error(f"Expected 8, got {metrics.suggestions_shown}")
        return False

    print_success("suggestions_shown counter increments correctly")
    return True


def test_increment_suggestions_clicked():
    """Test suggestions_clicked counter."""
    print("\n5. Testing suggestions_clicked increment...")

    metrics = BotMetrics()

    metrics.increment_suggestions_clicked()
    if metrics.suggestions_clicked != 1:
        print_error(f"Expected 1, got {metrics.suggestions_clicked}")
        return False

    metrics.increment_suggestions_clicked()
    if metrics.suggestions_clicked != 2:
        print_error(f"Expected 2, got {metrics.suggestions_clicked}")
        return False

    print_success("suggestions_clicked counter increments correctly")
    return True


def test_increment_status_updates_cached():
    """Test status_updates_cached counter."""
    print("\n6. Testing status_updates_cached increment...")

    metrics = BotMetrics()

    metrics.increment_status_updates_cached()
    if metrics.status_updates_cached != 1:
        print_error(f"Expected 1, got {metrics.status_updates_cached}")
        return False

    metrics.increment_status_updates_cached()
    metrics.increment_status_updates_cached()
    if metrics.status_updates_cached != 3:
        print_error(f"Expected 3, got {metrics.status_updates_cached}")
        return False

    print_success("status_updates_cached counter increments correctly")
    return True


def test_increment_status_correlations_shown():
    """Test status_correlations_shown counter."""
    print("\n7. Testing status_correlations_shown increment...")

    metrics = BotMetrics()

    metrics.increment_status_correlations_shown()
    if metrics.status_correlations_shown != 1:
        print_error(f"Expected 1, got {metrics.status_correlations_shown}")
        return False

    metrics.increment_status_correlations_shown()
    if metrics.status_correlations_shown != 2:
        print_error(f"Expected 2, got {metrics.status_correlations_shown}")
        return False

    print_success("status_correlations_shown counter increments correctly")
    return True


def test_suggestion_ctr_calculation():
    """Test click-through rate calculation."""
    print("\n8. Testing suggestion_ctr() calculation...")

    metrics = BotMetrics()

    # Test with no suggestions shown (avoid division by zero)
    ctr = metrics.suggestion_ctr()
    if ctr != 0.0:
        print_error(f"Expected 0.0 for no suggestions, got {ctr}")
        return False

    # Test with some suggestions shown
    metrics.increment_suggestions_shown(10)
    metrics.increment_suggestions_clicked()
    metrics.increment_suggestions_clicked()  # 2 clicks out of 10 shown

    ctr = metrics.suggestion_ctr()
    expected = 20.0  # 2/10 * 100 = 20%
    if abs(ctr - expected) > 0.01:
        print_error(f"Expected {expected}, got {ctr}")
        return False

    # Test with more data
    metrics.increment_suggestions_shown(20)
    metrics.increment_suggestions_clicked()  # 3 clicks out of 30 shown

    ctr = metrics.suggestion_ctr()
    expected = 10.0  # 3/30 * 100 = 10%
    if abs(ctr - expected) > 0.01:
        print_error(f"Expected {expected}, got {ctr}")
        return False

    print_success("suggestion_ctr() calculation works correctly")
    return True


def test_summary_format():
    """Test summary string format."""
    print("\n9. Testing summary() format...")

    metrics = BotMetrics()

    # Add some data
    metrics.increment_questions()
    metrics.increment_answers_sent()
    metrics.increment_reaction_searches()
    metrics.increment_slash_commands()
    metrics.increment_suggestions_shown(5)
    metrics.increment_suggestions_clicked()
    metrics.increment_status_updates_cached()
    metrics.increment_status_correlations_shown()

    summary = metrics.summary()

    # Check that all new sections are present
    required_sections = [
        "Bot Metrics:",
        "Suggestion Features:",
        "Status Monitoring:",
        "Reaction searches:",
        "Slash commands:",
        "Suggestions shown:",
        "Suggestions clicked:",
        "Click-through rate:",
        "Status updates cached:",
        "Status correlations shown:",
    ]

    for section in required_sections:
        if section not in summary:
            print_error(f"Missing section in summary: {section}")
            return False

    # Check values are correct
    if "Reaction searches: 1" not in summary:
        print_error("Reaction searches value not in summary")
        return False

    if "Slash commands: 1" not in summary:
        print_error("Slash commands value not in summary")
        return False

    if "Suggestions shown: 5" not in summary:
        print_error("Suggestions shown value not in summary")
        return False

    if "Suggestions clicked: 1" not in summary:
        print_error("Suggestions clicked value not in summary")
        return False

    if "Click-through rate: 20.0%" not in summary:
        print_error("CTR value not in summary")
        return False

    if "Status updates cached: 1" not in summary:
        print_error("Status updates cached value not in summary")
        return False

    if "Status correlations shown: 1" not in summary:
        print_error("Status correlations shown value not in summary")
        return False

    print_success("Summary format includes all new metrics")
    return True


def test_combined_metrics_tracking():
    """Test realistic usage scenario with multiple metrics."""
    print("\n10. Testing combined metrics tracking scenario...")

    metrics = BotMetrics()

    # Simulate user workflow:
    # 1. User reacts to message with 🔍
    metrics.increment_reaction_searches()

    # 2. Bot shows 5 FAQ suggestions
    metrics.increment_suggestions_shown(5)

    # 3. User clicks one suggestion
    metrics.increment_suggestions_clicked()

    # 4. Bot posts answer
    metrics.increment_answers_sent()

    # 5. Another user uses /ask command
    metrics.increment_slash_commands()

    # 6. Bot shows 3 suggestions
    metrics.increment_suggestions_shown(3)

    # 7. Status update gets cached
    metrics.increment_status_updates_cached()

    # 8. Status shown in answer
    metrics.increment_status_correlations_shown()

    # Verify all counters
    if metrics.reaction_searches != 1:
        print_error(f"reaction_searches should be 1, got {metrics.reaction_searches}")
        return False

    if metrics.slash_commands != 1:
        print_error(f"slash_commands should be 1, got {metrics.slash_commands}")
        return False

    if metrics.suggestions_shown != 8:  # 5 + 3
        print_error(f"suggestions_shown should be 8, got {metrics.suggestions_shown}")
        return False

    if metrics.suggestions_clicked != 1:
        print_error(f"suggestions_clicked should be 1, got {metrics.suggestions_clicked}")
        return False

    if metrics.answers_sent != 1:
        print_error(f"answers_sent should be 1, got {metrics.answers_sent}")
        return False

    if metrics.status_updates_cached != 1:
        print_error(f"status_updates_cached should be 1, got {metrics.status_updates_cached}")
        return False

    if metrics.status_correlations_shown != 1:
        print_error(
            f"status_correlations_shown should be 1, got {metrics.status_correlations_shown}"
        )
        return False

    # Check CTR
    ctr = metrics.suggestion_ctr()
    expected = 12.5  # 1/8 * 100
    if abs(ctr - expected) > 0.01:
        print_error(f"CTR should be {expected}, got {ctr}")
        return False

    print_success("Combined metrics tracking works correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  TESTING PHASE 7: METRICS TRACKING")
    print("=" * 60)

    tests = [
        test_metrics_initialization,
        test_increment_reaction_searches,
        test_increment_slash_commands,
        test_increment_suggestions_shown,
        test_increment_suggestions_clicked,
        test_increment_status_updates_cached,
        test_increment_status_correlations_shown,
        test_suggestion_ctr_calculation,
        test_summary_format,
        test_combined_metrics_tracking,
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
            print("\n✨ Phase 7 implementation verified!")
            print("   - Metrics tracking enhanced with new counters")
            print("   - Reaction search metrics added")
            print("   - Slash command metrics added")
            print("   - Suggestion display/click metrics added")
            print("   - Status monitoring metrics added")
            print("   - CTR calculation working correctly")
            print("   - Summary format updated")
            print("\nNext step: Phase 8 - Integrate all components")
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
