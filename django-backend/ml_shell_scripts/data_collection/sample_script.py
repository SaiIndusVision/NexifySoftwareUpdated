import time
import sys

def count_numbers(start, end):
    if start > end:
        print("⚠️ Starting number must be less than or equal to the ending number.")
        return

    for number in range(start, end + 1):
        print(f"Counting: {number}")
        time.sleep(1)

    print("✅ Counting completed!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("❌ Usage: python script.py <start> <end>")
    else:
        try:
            start = int(sys.argv[1])
            end = int(sys.argv[2])
            count_numbers(start, end)
        except ValueError:
            print("❌ Please enter valid integers.")
