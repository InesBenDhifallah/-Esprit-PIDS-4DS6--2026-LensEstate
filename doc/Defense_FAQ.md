# 🎓 Préparation à la Soutenance — Questions & Réponses Techniques

Ce document est conçu pour vous aider à répondre aux questions probables de votre professeur lors de la présentation du projet LensEstate.

---

## 🧠 Questions sur l'Intelligence Artificielle (ML/DS)

### 1. Pourquoi avoir choisi CatBoost plutôt que XGBoost ou Random Forest ?
**Réponse :** CatBoost est particulièrement performant avec les données catégorielles (comme la ville ou le type de bien) sans nécessiter de One-Hot Encoding manuel complexe. Il gère mieux les valeurs manquantes et réduit le risque d'overfitting grâce à son algorithme de "Ordered Boosting".

### 2. Qu'est-ce que le modèle multimodal et comment fonctionne la fusion ?
**Réponse :** C'est un modèle qui combine plusieurs types de sources (Texte, Image, Tabulaire). Nous utilisons une **fusion tardive (Late Fusion)** : nous extrayons des caractéristiques numériques du texte (via MiniLM) et de l'image (via ResNet50), puis nous les concaténons aux données tabulaires classiques pour former un seul vecteur de 130 caractéristiques envoyé au régresseur final.

### 3. Pourquoi utiliser la PCA (Analyse en Composantes Principales) ?
**Réponse :** Les modèles NLP et Vision génèrent des vecteurs très larges (ex: 2048 dimensions pour ResNet50). Utiliser autant de variables ralentirait le modèle et causerait du "bruit". La PCA nous permet de réduire ces vecteurs (ex: de 2048 à 64 dimensions) tout en conservant plus de 90% de l'information (variance), ce qui rend le modèle plus rapide et plus robuste.

### 4. Comment gérez-vous les données textuelles en Arabe et en Français ?
**Réponse :** Nous utilisons le modèle `paraphrase-multilingual-MiniLM-L12-v2`. C'est un modèle "Transformer" pré-entraîné sur plus de 50 langues, ce qui lui permet de comprendre la sémantique (le sens) des descriptions, qu'elles soient écrites en Français, en Arabe ou même en "Tunsi".

---

## 💻 Questions sur le Développement Web (Fullstack)

### 5. Pourquoi avoir séparé le Backend (Django) et le Frontend (React) ?
**Réponse :** Cette architecture "découplée" permet une meilleure scalabilité. Le backend peut servir d'API pour d'autres clients (application mobile future, par exemple) tandis que le frontend React offre une expérience utilisateur fluide (SPA - Single Page Application) sans rechargement de page.

### 6. Comment sécurisez-vous l'accès à l'API de prédiction ?
**Réponse :** Nous utilisons des jetons **JWT (JSON Web Tokens)**. L'utilisateur doit s'authentifier pour obtenir un access token. Côté Backend, la vue `PredictPriceView` utilise `IsAuthenticated`, ce qui bloque toute requête ne possédant pas un jeton valide.

### 7. Comment avez-vous géré le support de l'Arabe (RTL) en CSS ?
**Réponse :** Nous utilisons l'attribut HTML `dir="rtl"` ou `dir="ltr"` selon la langue sélectionnée. Avec **Tailwind CSS**, nous utilisons des classes logiques ou des ajustements dynamiques (ex: `${lang === "ar" ? "right-3" : "left-3"}`) pour inverser les icônes et le texte sans casser la mise en page.

---

## 🏗️ Architecture & Workflow

### 8. Quel est le rôle de `services.py` dans le backend ?
**Réponse :** C'est la couche "Métier" (Business Logic). Elle isole la complexité de l'IA de la vue Django. Elle s'occupe du chargement des modèles, du redimensionnement des images, de l'appel aux Transformers et du calcul final. Cela rend le code plus propre et facile à maintenir.

### 9. Comment gérez-vous le chargement des modèles pour ne pas ralentir le serveur ?
**Réponse :** Les modèles (CatBoost, NLP, Vision) sont chargés **une seule fois** au démarrage du serveur (global variables). Ainsi, chaque requête de prédiction est instantanée car elle n'a pas besoin de recharger plusieurs gigaoctets de données en mémoire à chaque fois.

### 10. Quelles sont les limites actuelles du projet et les améliorations possibles ?
**Réponse :**
- **Limites** : Le dataset d'entraînement est limité à une période donnée.
- **Améliorations** :
    - Ajouter le "Scraping" en temps réel pour mettre à jour les prix.
    - Utiliser des modèles de vision plus récents comme les ViT (Vision Transformers).
    - Intégrer une carte thermique (Heatmap) des prix par zone géographique.

---

## 📈 Métriques de Performance
- **Modèle** : CatBoost Regressor.
- **RMSE** : ~179,000 DT (sur le jeu de validation).
- **Features** : 130 (Tabulaires + NLP + Vision).
- **Temps de réponse** : ~1.5 seconde par prédiction (incluant l'analyse d'image).
