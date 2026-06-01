# 🎯 Guide configuration des 10 tools dans ElevenLabs

**Pour Yves** — copie/colle ce qui est en `code` directement dans ElevenLabs.

---

## ⚙️ ACCÈS

1. Aller sur **elevenlabs.io** → connecte-toi
2. Menu gauche → **"Agents"** → clique sur **Norah**
3. Onglet **"Outils"** (ou "Tools")
4. Bouton **"+ Ajouter un outil"** → **"Webhook"**

---

## 🔐 CONFIGURATION COMMUNE À TOUS LES TOOLS

Pour chacun des 10 tools, configure :

| Champ | Valeur |
|---|---|
| Type | **Webhook** |
| Méthode | **POST** (sauf `dashboard-data` qui est GET) |
| Headers | `Content-Type: application/json` ET `x-internal-secret: Norvex2026!` |
| Authentification | Aucune (l'auth se fait via le header `x-internal-secret`) |

---

## 📋 LES 10 TOOLS À CRÉER

### 1️⃣ verify_caller_identity

| | |
|---|---|
| **Name** | `verify_caller_identity` |
| **Description** | `Identifie un appelant et envoie un code 2FA par SMS. À utiliser quand un appelant veut accéder à un dossier.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-verify-identity` |
| **Body params** | `caller_phone` (string, E.164 format ex +15145551234), `role_hint` (enum: client, courtier, partenaire, yves) |

---

### 2️⃣ validate_code

| | |
|---|---|
| **Name** | `validate_code` |
| **Description** | `Valide le code 2FA reçu par SMS. À utiliser après que l'appelant a dit son code à voix haute.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-validate-code` |
| **Body params** | `caller_phone` (string), `code` (string, 4-8 chiffres), `role` (enum: client, courtier, partenaire, yves) |

---

### 3️⃣ get_dossier_status

| | |
|---|---|
| **Name** | `get_dossier_status` |
| **Description** | `Retourne les FAITS d'un dossier (étape, statut, dernière mise à jour). JAMAIS de décisions (taux, montant approuvé). Exige une session 2FA valide.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-get-dossier-status` |
| **Body params** | `caller_phone` (string), `dossier_id` (string) |

---

### 4️⃣ list_documents

| | |
|---|---|
| **Name** | `list_documents` |
| **Description** | `Liste les documents reçus et manquants pour un dossier. Exige session 2FA.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-list-documents` |
| **Body params** | `caller_phone` (string), `dossier_id` (string) |

---

### 5️⃣ get_next_steps

| | |
|---|---|
| **Name** | `get_next_steps` |
| **Description** | `Retourne l'étape actuelle (1-8) du pipeline et la prochaine étape attendue. Exige session 2FA.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-get-next-steps` |
| **Body params** | `caller_phone` (string), `dossier_id` (string) |

---

### 6️⃣ get_assigned_agent

| | |
|---|---|
| **Name** | `get_assigned_agent` |
| **Description** | `Retourne le nom et l'email de l'agent IA Analyste attitré au dossier. Exige session 2FA.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-get-assigned-agent` |
| **Body params** | `caller_phone` (string), `dossier_id` (string) |

---

### 7️⃣ schedule_callback

| | |
|---|---|
| **Name** | `schedule_callback` |
| **Description** | `Planifie un rappel par Yves. Pas besoin de 2FA. Niveau d'urgence: normal (digest 18h), vip (SMS+email Yves), urgent (SMS Yves immédiat).` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-schedule-callback` |
| **Body params** | `caller_phone` (string), `caller_name` (string optionnel), `reason` (string), `urgency` (enum: normal, vip, urgent), `notes` (string optionnel) |

---

### 8️⃣ log_call_summary

| | |
|---|---|
| **Name** | `log_call_summary` |
| **Description** | `Enregistre le résumé de l'appel à la fin de la conversation. Si qualified=true, envoie un email à Yves. À appeler à la FIN de chaque appel.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-log-call` |
| **Body params** | `caller_phone` (string), `scenario` (enum: voir liste ci-dessous), `summary` (string), `action_taken` (string), `qualified` (bool), `caller_role` (string optionnel), `dossier_id` (string optionnel) |

**Scénarios valides** : `promoteur_premiere_fois`, `courtier_nouveau_dossier`, `courtier_verifie_statut`, `client_avancement`, `info_generale`, `co_preteur`, `notaire_closing`, `avocat_partenaire`, `urgence_closing`, `client_insiste_yves`, `appelant_hostile`, `journaliste_media`, `courtier_non_accredite`, `hors_territoire`, `hors_fourchette`, `spam_ou_raccroche`, `autre`

---

### 9️⃣ send_application_link

| | |
|---|---|
| **Name** | `send_application_link` |
| **Description** | `Envoie un SMS à l'appelant avec le bon lien selon son besoin. Pas de 2FA. promoteur=formulaire Score Norvex, courtier=accréditation, upload=portail documents.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-send-link` |
| **Body params** | `caller_phone` (string), `type` (enum: promoteur, courtier, upload) |

---

### 🔟 alert_yves

| | |
|---|---|
| **Name** | `alert_yves` |
| **Description** | `Déclenche le PROTOCOLE VIP — SMS instantané + email à Yves. À utiliser pour: co-prêteur, notaire closing, avocat partenaire, urgence closing, journaliste, escalade client.` |
| **URL** | `https://capitalnorvex.com/.netlify/functions/norah-alert-yves` |
| **Body params** | `level` (enum: vip, urgent, critical), `summary` (string court), `caller_phone` (string), `caller_name` (string optionnel), `caller_role` (string optionnel), `detail` (string optionnel) |

---

## 🧪 TEST RAPIDE (à faire APRÈS configuration)

Une fois les 10 tools créés, fais un appel test au **+1 438-533-7738** :
1. Dis : *"Bonjour, je suis Yves Barrette, j'aimerais voir mes appels."*
2. Norah devrait appeler `verify_caller_identity` avec `role_hint=yves`
3. Tu devrais recevoir un SMS avec un code 4-6 chiffres
4. Dis le code à Norah → elle appelle `validate_code`
5. Si tout marche → session active

---

## 📊 DASHBOARD APPELS

Adresse : **https://capitalnorvex.com/capital-norvex-talk.html**
Mot de passe : `Norvex2026!`

Auto-refresh toutes les 60 secondes.

---

## ⚠️ NOTES IMPORTANTES

1. **Le 2FA Twilio Verify** par défaut autorise 5 essais et expire après 10 min.
   → Pour respecter le brief (max 3 essais, 5 min), va sur **Twilio Console** → Verify → Service `VFGAAT24H1JJ71BCHC24L51Z` → règle ces paramètres.

2. **Le digest 18h** s'enverra automatiquement chaque jour à 22:00 UTC (= 18h EDT en été, 17h EST en hiver). Pas d'action requise.

3. **Les 4 fonctions Netlify en 401** (trackAlerts, get-approved-dossiers, get-new-dossiers, list-pending) ont été corrigées via la mise à jour du `.env` de l'agent Python. Elles fonctionneront dès le prochain run de l'agent.

4. **Les partenaires VIP** doivent être ajoutés manuellement dans Firestore (collection `partenaires`) avec le schéma : `{phone, fullName, prenom, nom, organisation, categorie, dossiers_conjoints}`. Sans cela, les co-prêteurs ne seront pas reconnus comme VIP.

---

**Production déployée le 2 mai 2026 par Claude Code.**
**Site : https://capitalnorvex.com**
**Cible go-live : lundi 4 mai 2026, 08h00 EST.**
