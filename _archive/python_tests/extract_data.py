"""
Simple script to extract key data from Petri .eval files for verification

This script extracts the judge scores, full reasoning, and scoring criteria
that enable verification of the study's criterion-referenced evaluation methodology.

Usage:
    python extract_data.py path/to/eval_file.eval
"""

import json
import zipfile
import sys
from pathlib import Path


def extract_eval_data(eval_path):
    """Extract key data from a single .eval file"""
    
    eval_path = Path(eval_path)
    
    # Create temporary extraction directory
    extract_dir = Path('temp_extract')
    extract_dir.mkdir(exist_ok=True)
    
    # Extract the zip archive
    with zipfile.ZipFile(eval_path, 'r') as z:
        z.extractall(extract_dir)
    
    # Load the main sample data
    sample_file = extract_dir / 'samples' / '1_epoch_1.json'
    with open(sample_file, encoding='utf-8') as f:
        data = json.load(f)
    
    # Load header to get scoring criteria
    header_file = extract_dir / 'header.json'
    with open(header_file, encoding='utf-8') as f:
        header = json.load(f)
    
    # Extract key information
    result = {
        'eval_id': data.get('id'),
        'seed_instructions': data['input'],
        'transcript': data['messages'],
        'judge_scores': data['scores']['alignment_judge']['value'],
        'judge_explanation': data['scores']['alignment_judge']['explanation'],
        'judge_summary': data['scores']['alignment_judge']['answer'],
        'scoring_criteria': header['eval']['scorers'][0]['options']['dimensions'],
        'metadata': data.get('metadata', {})
    }
    
    # Clean up temporary directory
    import shutil
    shutil.rmtree(extract_dir)
    
    return result


def print_summary(data):
    """Print a comprehensive summary for verification"""
    
    print(f"\n{'='*70}")
    print(f"EVALUATION FILE VERIFICATION")
    print(f"{'='*70}\n")
    
    print(f"Eval ID: {data['eval_id']}")
    print(f"Transcript Length: {len(data['transcript'])} messages\n")
    
    print("=" * 70)
    print("JUDGE SCORES (These are the findings)")
    print("=" * 70)
    for dimension, score in data['judge_scores'].items():
        print(f"  {dimension}: {score}/10")
    
    print("\n" + "=" * 70)
    print("SCORING CRITERIA (What each score means)")
    print("=" * 70)
    for dimension, description in data['scoring_criteria'].items():
        print(f"\n{dimension}:")
        # Clean up the description formatting
        clean_desc = description.replace('{}', 'SCORE').strip()
        print(f"  {clean_desc}")
    
    print("\n" + "=" * 70)
    print("JUDGE SUMMARY")
    print("=" * 70)
    print(data['judge_summary'])
    
    print("\n" + "=" * 70)
    print("JUDGE DETAILED EXPLANATION")
    print("=" * 70)
    print(data['judge_explanation'])
    
    print("\n" + "=" * 70)
    print("SEED INSTRUCTIONS (First 500 characters)")
    print("=" * 70)
    print(data['seed_instructions'][:500] + "..." if len(data['seed_instructions']) > 500 else data['seed_instructions'])
    print()


def save_full_extraction(data, output_file):
    """Save complete extracted data to JSON file"""
    # Remove transcript to keep file size manageable
    # (transcript can be extracted separately if needed)
    save_data = {k: v for k, v in data.items() if k != 'transcript'}
    save_data['transcript_message_count'] = len(data['transcript'])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_data.py path/to/eval_file.eval")
        print("\nThis script extracts judge scores, reasoning, and criteria for verification.")
        sys.exit(1)
    
    eval_path = sys.argv[1]
    
    print(f"Extracting verification data from: {eval_path}")
    data = extract_eval_data(eval_path)
    print_summary(data)
    
    # Optionally save to JSON file
    # output_file = Path(eval_path).stem + '_verification.json'
    # save_full_extraction(data, output_file)
    # print(f"\nFull verification data saved to: {output_file}")

