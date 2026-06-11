from flask import Flask, request, jsonify
import pickle
import numpy as np

app = Flask(__name__)

# Load the trained model and vectorizer
model = pickle.load(open("depression_model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        
        if not data or "journal" not in data:
            return jsonify({"error": "No journal text provided"}), 400
        
        journal = data["journal"]
        
        # Transform the text using the vectorizer
        vector = vectorizer.transform([journal])
        
        # Get prediction
        prediction = model.predict(vector)[0]
        
        # Get prediction probabilities for confidence score
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(vector)[0]
            confidence = float(np.max(probabilities))
            depression_prob = float(probabilities[1]) if len(probabilities) > 1 else confidence
        else:
            confidence = None
            depression_prob = None
        
        # Map prediction to risk level based on binary classification
        # 0 = No depression, 1 = Depression detected
        if prediction == 0:
            risk = "Low"
        else:
            # For depression cases, use probability to determine severity
            if depression_prob and depression_prob >= 0.75:
                risk = "High"
            elif depression_prob is not None and depression_prob >= 0.55:
                risk = "Moderate"
            else:
                risk = "Moderate"
        
        response = {"risk": risk}
        if confidence is not None:
            response["confidence"] = confidence
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)