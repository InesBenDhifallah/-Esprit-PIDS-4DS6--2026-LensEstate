# 🚀 LensEstate : Guide Technique Ultra-Détaillé (Expert)

Ce document est une analyse profonde de l'architecture et du code du projet LensEstate.

---

## 🏗️ 1. Architecture Globale
LensEstate utilise une architecture **découplée (Decoupled Architecture)** :
-   **Backend** : Django REST Framework (Python). Il gère les données, l'auth et l'IA.
-   **Frontend** : React + Vite (TypeScript). Il gère l'interface et l'expérience utilisateur.
-   **Communication** : API REST sécurisée via des jetons **JWT (JSON Web Tokens)**.

---

## 🐍 2. Backend (Django) - Le Détail du Détail

### A. Configuration Globale (`lenstate/settings.py`)
-   **CORS (Cross-Origin Resource Sharing)** : Configuré pour autoriser le frontend (React) à envoyer des requêtes au backend. Sans cela, le navigateur bloquerait tout.
-   **INSTALLED_APPS** : Nous avons modularisé le code en 3 apps : `users` (comptes), `listings` (annonces) et `predictions` (IA).
-   **REST_FRAMEWORK** : Configuré pour utiliser `JWTAuthentication`. Cela signifie que chaque requête doit avoir un header `Authorization: Bearer <token>`.

### B. Le Système d'Authentification (`users/`)
-   **Modèle User** : Étend le modèle Django par défaut pour inclure le téléphone et l'avatar.
-   **SimpleJWT** : Utilise une clé secrète pour générer des jetons d'accès (valables 60 min) et de rafraîchissement.

### C. Le Moteur de Prédiction (`predictions/services.py`)
C'est ici que la magie opère.
1.  **Prétraitement** : Les données textuelles sont nettoyées (suppression des caractères spéciaux, mise en minuscule).
2.  **Multimodalité** :
    *   **Vision** : On utilise **ResNet50** (un réseau de neurones convolutifs). On retire la dernière couche (classification) pour obtenir des "features" brutes (caractéristiques visuelles).
    *   **NLP** : On utilise **MiniLM** (un Transformer). Il transforme une phrase en un vecteur de sens (embedding).
    *   **PCA (Principal Component Analysis)** : C'est crucial. ResNet et MiniLM donnent trop de données. La PCA réduit ces vecteurs (32 pour le texte, 64 pour l'image) pour ne garder que l'essentiel et éviter le "sur-apprentissage".
3.  **Inférence CatBoost** : Le modèle final combine les 130 caractéristiques et prédit le prix.

---

## ⚛️ 3. Frontend (React) - Le Détail du Détail

### A. Structure des Routes (`frontend/src/routes/`)
-   **TanStack Router** : Utilisé pour un routage "Type-Safe". Chaque fichier `.tsx` dans ce dossier correspond à une page (ex: `/price-prediction`).
-   **Navigation Asynchrone** : Les pages se chargent sans recharger le navigateur pour une sensation de "fluidité" (Single Page Application).

### B. Logique de Prédiction (`price-prediction.tsx`)
-   **État du Formulaire (`useState`)** : Un objet complexe stocke en temps réel tout ce que l'utilisateur tape ou coche.
-   **Gestion des Langues (i18n)** : Nous n'utilisons pas de bibliothèque lourde, mais un objet `T` constant qui contient les traductions FR et AR. La direction `rtl` (Right-to-Left) est activée dynamiquement pour l'Arabe.
-   **Envoi des Données** : Comme nous envoyons des fichiers (images) et du texte, nous utilisons `FormData`. C'est le seul format qui permet d'envoyer des "blobs" (données binaires) via une API.

---

## 🧠 4. Le Pipeline de l'IA (Mathématiques & Logique)

### Pourquoi 130 caractéristiques ?
Le modèle ne peut pas "lire" ou "voir" directement. Tout doit être transformé en chiffres :
1.  **34 variables numériques/catégorielles** : (Surface, Ville, Piscine...).
2.  **32 variables de texte** : Représentent le "sens" de la description.
3.  **64 variables d'image** : Représentent le "style" visuel.
**Somme = 130.**

### Pourquoi CatBoost ?
Nous avons choisi CatBoost plutôt que XGBoost car il gère nativement les variables catégorielles (comme le nom des villes) sans avoir besoin de faire du "One-Hot Encoding" manuel complexe, ce qui améliore la précision.

---

## ⚙️ 5. Configurations & Sécurité
-   **`.env`** : Contient les clés secrètes et les identifiants de base de données. Il ne doit jamais être partagé.
-   **Middleware Axes** : Protège contre les attaques par "Brute Force" (bloque l'IP après trop de tentatives de connexion).
-   **Permissions DRF** : Chaque vue API est protégée. Si vous n'avez pas de jeton, vous recevez une erreur 401.

---

## 🛠️ 6. Guide de Lancement rapide
1.  **Backend** : `venv\activate` -> `python manage.py runserver`.
2.  **Frontend** : `npm run dev`.
3.  **Lien** : L'interface React appelle le backend via `http://localhost:8000/api/`.
