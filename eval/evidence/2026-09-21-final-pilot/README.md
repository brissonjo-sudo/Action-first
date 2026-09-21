# Campagne comportementale — 2026-09-21

Cette campagne compare dix réponses témoins et dix réponses produites avec les
instructions Action First. Les paires ont été mélangées avant deux jugements structurés.

## Résultat

- barrière de promotion : `pass` ;
- échecs obligatoires : `0` ;
- préférences sur les huit cas d'amélioration : Action First `9`, témoin `1`, égalité `6` ;
- modèle répondant : `gpt-5.6-sol` ;
- juges : `gpt-6-astra` et `gpt-5.5`.

Les témoins proviennent de la campagne initiale dont les identifiants, prompts et objectifs
comparatifs sont identiques. Les dix réponses Action First et les deux verdicts ont été
régénérés après les corrections. `evidence.json` contient les réponses finales, les
correspondances aveugles, les verdicts, les limites et les empreintes SHA-256 du skill et
de la banque de cas.

## Portée

Cette preuve confirme la campagne sur un seul modèle répondant. Elle ne démontre ni une
généralisation à tous les modèles ni l'adoption par des utilisateurs. Les juges sont deux
modèles distincts, pas des évaluateurs humains.

Le harness suit le schéma recommandé dans le guide OpenAI
[Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills) :
sorties capturées, contrôles déterministes et jugement structuré.

## Vérifier

```powershell
python scripts/run_evals.py verify eval/evidence/2026-09-21-final-pilot
```
