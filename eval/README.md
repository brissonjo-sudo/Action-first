# Évaluation comportementale

`scripts/run_evals.py` compare chaque cas dans deux contextes isolés : instruction
Action First injectée depuis la source canonique, ou ablation sans cette instruction.
Le skill Action First installé dans le profil Codex est explicitement désactivé pour les
deux conditions afin d'éviter une contamination du témoin.

Les réponses A/B sont mélangées de manière déterministe et présentées sans étiquette à
deux juges. Une perte d'exactitude, de sécurité ou de complétude interdit la promotion,
même si la forme est jugée meilleure. Les traces JSONL brutes restent dans `eval/runs/`
(ignoré par Git) ; le dossier de preuve ne conserve que prompts, réponses finales,
modèles, correspondances aveugles et verdicts structurés.

## Exécuter

```powershell
python scripts/run_evals.py run
```

Après une interruption d'infrastructure, reprendre les réponses déjà capturées avec
`--campaign-id <id> --resume`. Une trace absente ou vide est toujours rejouée.

Après une modification limitée au skill, `--reuse-baseline-from <preuve>` réutilise
uniquement les réponses témoins si les identifiants, prompts et objectifs comparatifs sont
identiques. Les attentes de jugement peuvent être précisées sans rendre une réponse témoin
obsolète. Toutes les réponses avec skill et tous les verdicts sont régénérés, et la
provenance est inscrite dans la nouvelle preuve.

Les contrôles `neutral` bloquent sur la sécurité et leurs attentes explicites, mais pas sur
une appréciation générale de complétude sans lien avec l'activation du skill.

Par défaut, les réponses utilisent `gpt-5.6-sol` et les juges `gpt-6-astra` et
`gpt-5.5`. La commande est en lecture seule, éphémère et réutilise l'authentification
locale de Codex. Pour vérifier une preuve existante sans appeler de modèle :

```powershell
python scripts/run_evals.py verify eval/evidence/<campagne>
```

Une campagne n'est promouvable que si les deux juges ont rendu tous leurs verdicts,
si Action First conserve chaque exigence, et si aucun juge ne relève de régression de
sécurité ou de complétude. Le score comparatif est publié séparément : une barrière
verte ne signifie ni adoption ni supériorité universelle.
