"""Sample customer emails and expected outputs for testing."""

# --- Example 1: Billing Issue ---

BILLING_EMAIL = {
    "subject": "Erreur sur ma facture d'électricité",
    "body": (
        "Bonjour,\n\n"
        "Je me permets de vous contacter car j'ai reçu ma facture d'électricité "
        "du mois de mars 2026 et le montant me semble anormalement élevé. "
        "Le montant indiqué est de 347,50€ alors que je paie habituellement "
        "environ 85€ par mois.\n\n"
        "Mon numéro de contrat est EL-2024-78542 et mon compteur porte le "
        "numéro 09-441-627.\n\n"
        "Pourriez-vous vérifier s'il n'y a pas eu une erreur de relevé ?\n\n"
        "Cordialement,\n"
        "Jean-Pierre Martin\n"
        "12 rue des Lilas, 69003 Lyon"
    ),
}

BILLING_EXPECTED = {
    "category": "billing",
    "confidence_min": 0.85,
    "sentiment": "negative",
    "urgency": "medium",
    "entities": {
        "customer_name": "Jean-Pierre Martin",
        "contract_id": "EL-2024-78542",
        "address": "12 rue des Lilas, 69003 Lyon",
        "date": "mars 2026",
        "amount": "347,50€",
        "meter_number": "09-441-627",
    },
}


# --- Example 2: Complaint ---

COMPLAINT_EMAIL = {
    "subject": "INACCEPTABLE - Coupure d'eau sans prévenir",
    "body": (
        "Madame, Monsieur,\n\n"
        "Je suis absolument furieux ! Depuis ce matin 6h, je n'ai plus d'eau "
        "dans mon appartement au 45 avenue Victor Hugo, 75016 Paris. "
        "PERSONNE ne nous a prévenus de cette coupure !\n\n"
        "J'ai deux enfants en bas âge et c'est totalement inadmissible de "
        "couper l'eau sans aucun préavis. J'ai essayé d'appeler votre service "
        "client 5 fois ce matin, impossible d'avoir quelqu'un !!!\n\n"
        "Mon numéro de client est CL-98712. Je vous demande une intervention "
        "IMMÉDIATE et un geste commercial pour ce désagrément.\n\n"
        "Paul Durand"
    ),
}

COMPLAINT_EXPECTED = {
    "category": "complaint",
    "confidence_min": 0.90,
    "sentiment": "angry",
    "urgency": "high",
    "entities": {
        "customer_name": "Paul Durand",
        "contract_id": "CL-98712",
        "address": "45 avenue Victor Hugo, 75016 Paris",
    },
}


# --- Example 3: Move Request ---

MOVE_EMAIL = {
    "subject": "Déménagement - transfert de contrat gaz",
    "body": (
        "Bonjour,\n\n"
        "Je vous écris pour vous informer que je déménage le 15 mai 2026. "
        "Je quitte mon logement actuel au 8 place de la République, "
        "31000 Toulouse pour m'installer au 22 boulevard Gambetta, "
        "31000 Toulouse.\n\n"
        "Mon contrat gaz actuel porte le numéro GAZ-2023-11234. "
        "Je souhaiterais transférer mon contrat à ma nouvelle adresse.\n\n"
        "Pourriez-vous m'indiquer la marche à suivre et les documents "
        "nécessaires ?\n\n"
        "Merci d'avance,\n"
        "Sophie Lefebvre"
    ),
}

MOVE_EXPECTED = {
    "category": "move",
    "confidence_min": 0.90,
    "sentiment": "neutral",
    "urgency": "medium",
    "entities": {
        "customer_name": "Sophie Lefebvre",
        "contract_id": "GAZ-2023-11234",
        "date": "15 mai 2026",
    },
}
