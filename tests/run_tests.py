#!/usr/bin/env python
import sys
import pytest

def main():
    """
    Lance les tests avec pytest.
    Usage: python run_tests.py [chemin_du_test]
    Exemple: python run_tests.py tests/test_timers_async.py::TestTimersAsync::test_update_timer_channel_async
    """
    # Récupérer le chemin du test depuis les arguments
    test_path = sys.argv[1] if len(sys.argv) > 1 else "tests/"
    
    # Options de pytest
    pytest_args = [
        "-v",  # Mode verbeux
        "--cov=app",  # Couverture de code pour le package app
        "--cov-report=term-missing",  # Rapport de couverture détaillé
        test_path  # Chemin du test à exécuter
    ]
    
    # Lancer pytest avec les arguments
    sys.exit(pytest.main(pytest_args))

if __name__ == "__main__":
    main() 