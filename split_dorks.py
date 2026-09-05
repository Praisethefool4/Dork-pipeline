#!/usr/bin/env python3
"""
split_dorks.py - Splits a master dorks.txt file into N equal-ish partitions.
Designed for parallel worker execution on GitHub Actions.
"""
import sys
import os

def main():
    if len(sys.argv) < 4:
        print("Usage: python split_dorks.py <dorks_file> <runner_id> <total_runners>")
        print("Example: python split_dorks.py my_dorks.txt 5 19")
        sys.exit(1)
    
    dorks_file = sys.argv[1]
    runner_id = int(sys.argv[2])
    total_runners = int(sys.argv[3])
    
    if not os.path.exists(dorks_file):
        print(f"Error: Dork file '{dorks_file}' does not exist.")
        # Create an empty file to prevent scraper from crashing
        with open("dorks_runner.txt", "w", encoding="utf-8") as f:
            pass
        sys.exit(0)
        
    with open(dorks_file, "r", encoding="utf-8", errors="ignore") as f:
        dorks = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        
    if not dorks:
        print("Warning: Master dorks list is empty.")
        with open("dorks_runner.txt", "w", encoding="utf-8") as f:
            pass
        sys.exit(0)
        
    # Split dorks equally among runners
    chunk_size = len(dorks) // total_runners
    remainder = len(dorks) % total_runners
    
    # Calculate slice boundaries
    # Adjusting for 1-based runner ID (1 to 19)
    idx = runner_id - 1
    start = idx * chunk_size + min(idx, remainder)
    end = start + chunk_size + (1 if idx < remainder else 0)
    
    partitioned_dorks = dorks[start:end]
    
    with open("dorks_runner.txt", "w", encoding="utf-8") as f_out:
        for d in partitioned_dorks:
            f_out.write(d + "\n")
            
    print(f"Runner {runner_id}/{total_runners} assigned {len(partitioned_dorks)} dorks (lines {start+1} to {end})")

if __name__ == "__main__":
    main()
