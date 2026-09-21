# Action First

Des réponses d'agent qui commencent par le résultat ou la prochaine action.

## Installer

Demandez à votre agent :

```text
Installe le skill Action First depuis https://github.com/brissonjo-sudo/action-first.
Vérifie les fichiers avant l'installation et explique où il sera installé.
```

Ou copiez `skills/action-first/` dans le répertoire de skills de votre agent. Dans
Codex, invoquez `$action-first`. Dans Claude Code, invoquez `/action-first`.

Le mode reste actif pour la session jusqu'à « stop action first » ou « mode normal ».
L'installation seule ne l'active pas.

## Ce que cela change

**Avant**

> Bonne question. Plusieurs éléments sont à prendre en compte dans le flux
> d'authentification. Il pourrait être utile de commencer par vérifier la fonction,
> puis de regarder les tests et éventuellement les dépendances.

**Après**

> Ouvre `src/auth.ts:42` et vérifie l'appel à `verifyToken`.
>
> 1. Corrige l'appel.
> 2. Lance `npm test -- auth.spec.ts`.
> 3. Si le test échoue, relève la première erreur.

## Principes

- résultat ou action en premier ;
- étapes numérotées ;
- une priorité visible sans tronquer le contenu nécessaire ;
- progrès et erreurs décrits concrètement ;
- pas de préambule, digression ou clôture vide.

Action First est un format volontaire. Aucun diagnostic n'est requis ou inféré.
Le projet n'envoie aucune donnée et n'installe aucun service réseau.

## Compatibilité

Le format canonique est Agent Skills. Le dépôt fournit aussi des manifests Claude et
Codex. Pour Cursor, Copilot ou un autre agent compatible, copiez le dossier du skill
dans le chemin de découverte indiqué par l'outil.

## Vérifier

Demandez :

```text
Utilise Action First. Explique comment initialiser un dépôt Git vide.
```

La réponse doit commencer par la commande ou la première action, conserver toutes les
étapes nécessaires et ne pas ajouter de formule de clôture générique.

## Provenance et limites

Le projet est distinct de
[`Skills-accessibilite`](https://github.com/brissonjo-sudo/Skills-accessibilite), qui
reste la source rigoureuse des adaptations liées à des besoins explicitement déclarés.
Action First reprend des invariants de présentation généraux, sans transformer ces
invariants en affirmations cliniques.

Licence MIT. Voir [LICENSE](LICENSE).

Les brouillons de diffusion et la grille de mesure à J+7/J+30 sont dans [`docs/`](docs/).
