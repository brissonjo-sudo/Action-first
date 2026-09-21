# Installation

## Agent Skills

Copier `skills/action-first/` dans le répertoire de skills reconnu par l'agent, puis
démarrer une nouvelle session. L'installation doit être contrôlée avec une question de
vérification ; la seule présence du dossier ne prouve pas que les règles sont appliquées.

## Codex

Le skill s'invoque avec `$action-first`. Le fichier `agents/openai.yaml` interdit
l'activation implicite. Le manifest `.codex-plugin/plugin.json` est prêt pour un
catalogue ou une installation de plugin compatible.

## Claude Code

Le skill s'invoque avec `/action-first`. Sa description limite la sélection aux demandes
explicites d'Action First ou de ce format. Le format Agent Skills commun ne fournit pas
de verrou d'invocation portable équivalent à la politique Codex.

## Désactivation

Dire « stop action first » ou « mode normal ». Pour un retrait permanent, supprimer le
skill ou le plugin avec la commande documentée par l'agent utilisé.
