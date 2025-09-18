# cli/cli.py
import argparse
from ..controller import run_all_lenses

def main():
    parser = argparse.ArgumentParser(description="Run EqualityMatrix Lenses")
    parser.add_argument("text", type=str, help="Input text to evaluate")
    args = parser.parse_args()

    results = run_all_lenses(args.text)
    print("=== Lens Results ===")
    for lens, result in results.items():
        print(f"{lens}: {result['response']}")

if __name__ == "__main__":
    main()