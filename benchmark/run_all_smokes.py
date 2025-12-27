import subprocess
import sys


def run(cmd):
    print("\n==>", " ".join(cmd))
    r = subprocess.run(cmd, text=True)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main():
    run([sys.executable, "benchmark/adapter_numpy_smoke_test.py"])
    run([sys.executable, "benchmark/adapter_torch_smoke_test.py"])


if __name__ == "__main__":
    main()
