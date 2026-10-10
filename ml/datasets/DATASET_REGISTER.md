# Dataset Register

## Primary dataset
Name: Garbage Classification
Source: https://www.kaggle.com/datasets/mostafaabla/garbage-classification
Purpose: Training and evaluation of the EPRLens packaging image classifier.

## Source categories
Expected categories include battery, biological, brown-glass, cardboard,
clothes, green-glass, metal, paper, plastic, shoes, trash, and white-glass.

## Target classes
plastic, paper, cardboard, metal, glass, battery, trash_other

## Mapping policy
- brown-glass, green-glass, white-glass -> glass
- biological, clothes, shoes, trash -> trash_other
- plastic, paper, cardboard, metal, battery retain their labels

## Data quality
Corrupted images and duplicate images must be checked before splitting.
Train, validation, and test sets must be separated to avoid leakage.
