import pickle
import pandas as pd
import numpy as np
import sys
import os

from app import keyword_classify

def get_ml_breakdown(text, vectorizer, model):
    features = vectorizer.transform([text])
    feature_names = vectorizer.get_feature_names_out()
    
    # Get non-zero features
    non_zero_indices = features.nonzero()[1]
    
    try:
        coefs = model.coef_[0]
    except AttributeError:
        # Handle CalibratedClassifierCV
        try:
            coefs = model.calibrated_classifiers_[0].estimator.coef_[0]
        except AttributeError:
            coefs = model.calibrated_classifiers_[0].base_estimator.coef_[0]
    
    feature_breakdown = []
    for idx in non_zero_indices:
        word = feature_names[idx]
        tfidf_weight = features[0, idx]
        coef = coefs[idx]
        contribution = tfidf_weight * coef
        feature_breakdown.append({
            'word': word,
            'tfidf_weight': tfidf_weight,
            'coef': coef,
            'contribution': contribution
        })
        
    # Sort by contribution or tfidf_weight
    feature_breakdown.sort(key=lambda x: abs(x['contribution']), reverse=True)
    return feature_breakdown[:10]

def main():
    print("Loading models...")
    with open('depression_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
        
    phrases = [
        ("Case 2: Short positive", "I feel happy and grateful today, life is good."),
        ("Case 4: Short depressed", "I feel depressed and sad, cannot sleep.")
    ]
    
    for name, text in phrases:
        print(f"\n{'='*50}\n{name}: '{text}'\n{'='*50}")
        
        # 1. Keyword-layer breakdown
        risk, confidence, evidence, neg_score = keyword_classify(text)
        print("--- Keyword Layer ---")
        print(f"Neg Score: {neg_score}")
        print(f"Evidence Dict: {evidence}")
        
        # 2. ML Side
        prob = model.predict_proba(vectorizer.transform([text]))[0][1]
        print(f"\n--- ML Layer (Prob: {prob:.3f}) ---")
        breakdown = get_ml_breakdown(text, vectorizer, model)
        print(f"{'Word':<15} | {'TF-IDF Weight':<15} | {'Coef':<10} | {'Contribution'}")
        print("-" * 65)
        for item in breakdown:
            print(f"{item['word']:<15} | {item['tfidf_weight']:<15.4f} | {item['coef']:<10.4f} | {item['contribution']:.4f}")
            
        # 3. Token Count
        token_count = len(text.split())
        print(f"\n--- Sparsity Check ---")
        print(f"Token Count: {token_count}")
        
    print("\n" + "="*50)
    print("Loading Dataset to check average token count...")
    df = pd.read_csv('depression_dataset.csv')
    df['clean_text'] = df['clean_text'].astype(str)
    avg_tokens = df['clean_text'].apply(lambda x: len(x.split())).mean()
    median_tokens = df['clean_text'].apply(lambda x: len(x.split())).median()
    print(f"Dataset Average Token Count: {avg_tokens:.1f}")
    print(f"Dataset Median Token Count: {median_tokens:.1f}")

if __name__ == '__main__':
    main()
