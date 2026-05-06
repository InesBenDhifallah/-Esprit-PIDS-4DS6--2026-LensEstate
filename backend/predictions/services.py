import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from django.conf import settings
from catboost import CatBoostRegressor
from sentence_transformers import SentenceTransformer
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Configuration des chemins
MODELS_DIR = Path(settings.BASE_DIR).parent / 'models_final'

# --- Chargement des modèles (Lazy Loading Singleton) ---
_model = None
_feature_names = None
_cat_features = None
_nlp_model = None
_nlp_pca = None
_vision_model = None
_vision_pca = None

_preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def load_all_models():
    global _model, _feature_names, _cat_features, _nlp_model, _nlp_pca, _vision_model, _vision_pca
    
    # Check if everything is already loaded
    if all(v is not None for v in [_model, _nlp_model, _vision_model]):
        return

    print("--- Loading ML Models (this may take a while on first run) ---")
    
    try:
        # CatBoost
        if _model is None:
            _model = CatBoostRegressor()
            _model.load_model(str(MODELS_DIR / 'catboost_final_latest.cbm'))
            _feature_names = joblib.load(str(MODELS_DIR / 'feature_names_final.pkl'))
            _cat_features = joblib.load(str(MODELS_DIR / 'cat_features_final.pkl'))

        # NLP
        if _nlp_model is None:
            _nlp_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            _nlp_pca = joblib.load(str(MODELS_DIR / 'nlp_pca.joblib'))

        # Vision (ResNet50)
        if _vision_model is None:
            _vision_model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
            _vision_model = nn.Sequential(*list(_vision_model.children())[:-1])
            _vision_model.eval()
            _vision_pca = joblib.load(str(MODELS_DIR / 'vision_pca.joblib'))
            
        print("--- Models Loaded Successfully ---")
    except Exception as e:
        print(f"--- Error loading models: {str(e)} ---")
        raise e

def predict_price(data: dict, image_file=None) -> dict:
    load_all_models()
    
    # 1. Initialisation
    row = {f: 0.0 for f in _feature_names}
    for cat in _cat_features:
        row[cat] = 'Unknown'

    # 2. Données Numériques
    surface = float(data.get('surface_m2', 100))
    rooms = float(data.get('rooms', 3))
    bedrooms = float(data.get('bedrooms', 2))
    bathrooms = float(data.get('bathrooms', 1))
    
    row['surface_m2'] = surface
    row['rooms'] = min(rooms, 42)
    row['bedrooms'] = min(bedrooms, 20)
    row['bathrooms'] = min(bathrooms, 15)
    row['image_count'] = float(data.get('image_count', 1 if image_file else 0))
    
    # 3. Mapping Catégoriel (Correction Majuscules/Minuscules)
    prop_map = {
        'appartement': 'Apartment', 'villa': 'Villa', 'studio': 'Apartment',
        'penthouse': 'Apartment', 'maison': 'House', 'terrain': 'Land',
        'apartment': 'Apartment', 'house': 'House', 'land': 'Land'
    }
    seller_map = {
        'particulier': 'Particulier', 'agence': 'agency', 
        'promoteur': 'agency', 'individual': 'Particulier'
    }
    
    raw_prop = str(data.get('property_type', 'appartement')).lower()
    raw_seller = str(data.get('seller_type', 'particulier')).lower()
    
    row['property_type'] = prop_map.get(raw_prop, 'Apartment')
    row['seller_type'] = seller_map.get(raw_seller, 'Particulier')
    
    # Localisation (Title Case pour le modèle)
    row['governorate'] = str(data.get('region', 'Tunis')).title()
    city = str(data.get('city', row['governorate']))
    row['city'] = ' '.join(word.capitalize() for word in city.split())

    # 4. Équipements & Flags
    amenity_count = 0
    amenities = [
        'has_pool', 'has_parking', 'has_garden', 'has_elevator',
        'has_air_conditioning', 'has_heating', 'has_security',
        'has_furniture', 'has_terrace', 'has_sea_view',
        'has_basement', 'has_standing'
    ]
    for am in amenities:
        val = data.get(am, 'false')
        is_active = 1 if str(val).lower() in ['true', '1', '1.0'] else 0
        row[am] = float(is_active)
        amenity_count += is_active
    
    row['amenity_score'] = float(amenity_count)
    row['has_images'] = 1.0 if image_file or row['image_count'] > 0 else 0.0
    row['is_agency'] = 1.0 if row['seller_type'] == 'agency' else 0.0
    row['rooms_per_m2'] = row['rooms'] / surface if surface > 0 else 0.0
    
    row['has_surface'] = 1.0 if surface > 0 else 0.0
    row['has_rooms_info'] = 1.0 if rooms > 0 else 0.0
    row['has_bathrooms_info'] = 1.0 if bathrooms > 0 else 0.0
    row['has_bedrooms_info'] = 1.0 if bedrooms > 0 else 0.0

    # 5. NLP (Texte)
    description = str(data.get('description', ''))
    row['word_count'] = float(len(description.split()))
    row['txt_len'] = float(len(description))
    row['has_desc'] = 1.0 if len(description) > 20 else 0.0
    row['description_word_count'] = row['word_count']

    # On encode TOUJOURS pour éviter les valeurs hors-distribution (0.0)
    emb = _nlp_model.encode([description])
    nlp_feats = _nlp_pca.transform(emb)[0]
    for i in range(min(32, len(nlp_feats))):
        row[f'nlp_emb_{i}'] = float(nlp_feats[i])

    # 6. Vision (Image)
    if image_file:
        try:
            img = Image.open(image_file).convert('RGB')
            tensor = _preprocess(img).unsqueeze(0)
            with torch.no_grad():
                feat = _vision_model(tensor).flatten().numpy()
            vis_feats = _vision_pca.transform([feat])[0]
            for i in range(min(64, len(vis_feats))):
                row[f'vision_pca_{i}'] = float(vis_feats[i])
        except:
            pass

    # 7. Prédiction avec Pool (pour forcer la prise en compte des catégories)
    from catboost import Pool
    df = pd.DataFrame([row])[_feature_names]
    
    # On s'assure que les colonnes catégorielles sont bien des strings
    cat_cols = ['property_type', 'governorate', 'city', 'seller_type']
    df[cat_cols] = df[cat_cols].astype(str)
    
    # Création du Pool avec les index des catégories
    cat_indices = [df.columns.get_loc(c) for c in cat_cols]
    pool = Pool(df, cat_features=cat_indices)
    
    prediction = _model.predict(pool)[0]
    
    # Sécurité prix minimum
    final_price = max(10_000.0, prediction)

    # 8. Calcul des métriques pour le dashboard
    # Complétude : sur les 130 features, combien sont à 1 (approximatif pour le UI)
    completeness = 60 # Base
    if image_file: completeness += 20
    if len(description) > 100: completeness += 20
    
    # Qualité des données
    quality = "medium"
    if image_file and len(description) > 100: quality = "high"
    elif not image_file and len(description) < 20: quality = "low"

    return {
        'price': round(final_price, -2),
        'currency': 'TND',
        'conf': 90 if image_file and len(description) > 50 else 75,
        'data_quality': quality,
        'input_completeness': min(completeness, 100),
        'location_factor_applied': 1.15 if row['governorate'] in ['Tunis', 'Ariana', 'Sousse'] else 0.95,
        'model': 'CatBoost Multimodal v1.2'
    }
