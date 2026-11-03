import csv, sys, itertools

def main():
    path = sys.argv[1]
    with open(path, newline="") as f:
        for row in itertools.islice(csv.reader(f), 20):
            print(" | ".join(row))
