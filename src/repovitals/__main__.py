import sys

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("to use: uv run -m repovitals [path]")
        return 1

    print(f"RepoVitals {__import__('repovitals').__version__}")
    print(f"target: {args[0]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())