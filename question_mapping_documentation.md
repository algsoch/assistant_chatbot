# Question Mapping Documentation

## Overview

This document explains the structure and purpose of the `question_mapping.json` file, which maps questions to their corresponding Python script paths.

## File Structure

The JSON file contains a single root object with a "questions" array. Each entry in the array has two key fields:

1. `question`: The full text of a question or assignment
2. `mapped_script`: The file path to the Python script that answers or processes the question

## Purpose

This mapping system allows for:
- Organized tracking of questions and their solutions
- Quick access to the appropriate script for each question
- Systematic processing of multiple assignments (GA1, GA2, GA3, GA4)

## Example Entry

```json
{
    "question": "Install and run Visual Studio Code. In your Terminal (or Command Prompt), type code -s and press Enter. Copy and paste the entire output below.",
    "mapped_script": "E://data science tool//GA1//first.py"
}