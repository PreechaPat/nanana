import argparse

def main():
    parser = argparse.ArgumentParser(description="nanana: A sample command-line tool.")
    parser.add_argument("positional_arg", help="A positional argument.")
    parser.add_argument("-a", "--arg1", help="Optional argument 1.")
    parser.add_argument("-b", "--arg2", help="Optional argument 2.")
    parser.add_argument("-c", "--arg3", help="Optional argument 3.")

    args = parser.parse_args()

    print("how to use it:")
    print(f"nanana {args.positional_arg} -a <arg1> -b <arg2> -c <arg3>")
    print(f"  positional_arg: {args.positional_arg}")
    print(f"  arg1: {args.arg1}")
    print(f"  arg2: {args.arg2}")
    print(f"  arg3: {args.arg3}")

if __name__ == "__main__":
    main()
