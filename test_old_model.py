import pickle
import sys

def main():
    model_path = 'ai-depression-risk-assessment/backend/depression_model_backup_preaugment.pkl'
    vectorizer_path = 'ai-depression-risk-assessment/backend/vectorizer.pkl'
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)
    except Exception as e:
        print(f"Error loading models: {e}")
        return

    texts = [
        "I feel happy and grateful today, life is good.",
        "I feel depressed and sad, cannot sleep."
    ]
    
    features = vectorizer.transform(texts)
    predictions = model.predict(features)
    probabilities = model.predict_proba(features)[:, 1] if hasattr(model, 'predict_proba') else [None, None]
    
    print("Testing with old model and current vectorizer:")
    for text, pred, prob in zip(texts, predictions, probabilities):
        print(f"Text: '{text}' | Prediction: {pred} | Prob: {prob}")

if __name__ == "__main__":
    main()
