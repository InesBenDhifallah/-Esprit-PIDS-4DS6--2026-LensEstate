# 📘 Guide Technique Complet — Projet LensEstate

Ce document détaille l'architecture, le rôle de chaque fichier et le fonctionnement interne de la plateforme LensEstate, de la gestion des utilisateurs à la prédiction multimodal par IA.

---

## 1. ⚙️ Architecture du Backend (Django)

Le backend est construit avec **Django Rest Framework (DRF)**. Il suit une structure modulaire où chaque fonctionnalité est isolée dans une "application".

### A. Le Cœur : `lenstate/`
C'est le dossier de configuration globale.
- **`settings.py`** : Définit la base de données (PostgreSQL), active le CORS (pour que le React puisse communiquer avec le Django), et configure le JWT (Jetons d'authentification). Il contient aussi la liste `INSTALLED_APPS` (où nous avons ajouté `predictions`).
- **`urls.py`** : C'est l'aiguillage principal. Il redirige les requêtes vers les différentes applications : `/api/auth/`, `/api/listings/`, et `/api/predict/`.

### B. Gestion des Utilisateurs : `users/`
- **`models.py`** : Définit l'utilisateur (Username, Email, Phone).
- **`views.py`** : Gère l'inscription, la connexion et les jetons JWT (Access/Refresh).
- **`serializers.py`** : Transforme les objets Python en JSON pour le frontend.

### C. Le Moteur d'IA : `predictions/` (Le plus important)
Cette partie transforme les données brutes en estimation de prix.
- **`services.py`** :
    1.  **Chargement** : Charge le modèle `catboost_final_latest.cbm` et les réducteurs PCA au démarrage.
    2.  **Prétraitement** : Nettoie les données (minuscules, suppression des tirets) pour correspondre exactement à l'entraînement.
    3.  **NLP (Texte)** : Utilise `SentenceTransformer` pour convertir la description en un vecteur numérique (32 dimensions).
    4.  **Vision (Image)** : Utilise un modèle `ResNet50` (vision par ordinateur) pour extraire les caractéristiques visuelles de la photo (64 dimensions).
    5.  **Inférence** : Envoie les 130 caractéristiques finales au modèle CatBoost pour obtenir le prix final.
- **`views.py`** : Reçoit le formulaire du frontend (`POST /api/predict/`), vérifie que l'utilisateur est connecté (`IsAuthenticated`), appelle le service de prédiction et renvoie le prix.

---

## 2. 🎨 Architecture du Frontend (React + TypeScript)

Le frontend utilise **Vite** pour la rapidité et **TanStack Router** pour la navigation.

### A. Structure des Dossiers
- **`src/lib/`** : Contient le "moteur" de communication.
    - `api.ts` : Gère tous les appels `fetch` et ajoute automatiquement le jeton JWT dans les headers pour la sécurité.
    - `auth.ts` : Gère le stockage du jeton dans le `localStorage`.
- **`src/context/AuthContext.tsx`** : Un "magasin" global qui sait si l'utilisateur est connecté. Il permet de bloquer ou déverrouiller des fonctionnalités (comme la prédiction) partout dans l'app.
- **`src/routes/`** : Chaque fichier ici est une page.

### B. La Page de Prédiction : `price-prediction.tsx`
C'est la pièce maîtresse du projet. Elle est divisée en plusieurs logiques :
1.  **Gestion de la Langue (i18n)** : Un objet `T` contient toutes les traductions (Français/Arabe). Le bouton toggle change la langue et la direction du texte (`ltr` pour FR, `rtl` pour AR).
2.  **Le Formulaire** : Capturé via un état `form`. Il inclut des logiques d'autocomplétion pour les villes et des boutons interactifs pour les équipements (piscine, jardin, etc.).
3.  **Sécurité (Unlock)** : Si `isAuthenticated` est faux, le code cache le bouton de prédiction et affiche une carte demandant de se connecter.
4.  **Appel API** : Utilise `FormData` pour envoyer à la fois du texte et une image au serveur Django.
5.  **Affichage Premium** : Le résultat est affiché dans une carte avec des animations **Framer Motion**, montrant le prix, l'indice de confiance et la tendance du marché.

---

## 3. 🧠 Intégration du Modèle ML (Multimodal)

Le projet est dit "Multimodal" car il combine trois types de données :

1.  **Données Tabulaires** : Surface, pièces, étage, ville, équipements. Ce sont des chiffres ou des catégories.
2.  **Données Textuelles (NLP)** : Le modèle "comprend" la qualité de la description. Une description bien écrite avec des mots-clés de luxe peut augmenter l'estimation.
3.  **Données Visuelles (Vision)** : Si vous uploadez une photo, l'IA "voit" le standing du bien.

### Le Pipeline de Prédiction
Quand vous cliquez sur "Prédire" :
1.  **Front** → Envoie JSON + Image.
2.  **Back** → Reçoit l'image.
3.  **ResNet50** → Analyse l'image (0.5s).
4.  **MiniLM** → Analyse le texte (0.2s).
5.  **PCA** → Réduit la complexité des vecteurs.
6.  **CatBoost** → Rend le verdict final.
7.  **Front** → Affiche le prix avec un effet de fondu.

---

## 🛠️ Résumé des Fichiers Clés

| Partie | Fichier | Rôle Crucial |
|---|---|---|
| **Back** | `backend/predictions/services.py` | Charger l'IA et calculer le prix. |
| **Back** | `backend/lenstate/settings.py` | Configurer la sécurité et les apps. |
| **Front** | `src/routes/price-prediction.tsx` | Interface utilisateur, bilingue, et sécurité. |
| **Front** | `src/context/AuthContext.tsx` | Savoir si l'utilisateur est logué. |
| **Data** | `models_final/catboost_final_latest.cbm` | Le "cerveau" entraîné qui connaît les prix du marché. |

---

Ce projet est conçu pour être **production-ready** : il est sécurisé, internationalisé (FR/AR), et utilise les dernières technologies de Deep Learning (Vision/NLP) pour une précision maximale.
