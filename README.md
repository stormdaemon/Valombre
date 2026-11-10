# Valombre — Les Éclats de l'Aube

Action-RPG médiéval à la troisième personne qui tourne dans le navigateur (three.js, WebGL 2).
Monde ouvert d'environ 20 km², combats au corps à corps exigeants, six boss, quêtes, lore, création de
personnage détaillée. Tous les modèles, textures, animations et le terrain sont générés par des scripts
Blender du dépôt : aucun asset téléchargé, aucun service payant.

## Jouer

- Windows : double-cliquer sur `Jouer.bat` (il faut [Node.js](https://nodejs.org)).
- Ailleurs : `npm start` (ou `node server.mjs --open`), puis ouvrir http://localhost:5173.

Chrome ou Edge recommandés, en plein écran (F11). Au premier lancement, le jeu mesure la machine et
choisit la qualité graphique. Commandes et conseils : voir [`LISEZMOI.txt`](LISEZMOI.txt).

## Contenu

- **Monde** : île de 5,1 × 5,1 km (19,8 km² de terres) : relief érodé, rivière, routes, ponts, villages,
  port, phare, citadelle en ruine, marais, montagnes enneigées, terres de cendres.
- **Combat** : attaques légères et lourdes, garde et parade, roulade, verrouillage, endurance, postures,
  altérations d'état (poison, brûlure, gel), six pouvoirs d'Éclat, fioles améliorables.
- **Ennemis** : loups, araignées, squelettes, trolls, golems, bandits, cultistes, chevaliers creux.
  Boss : Croc-Blême le Grand Alpha, Arakha la Reine Tisseuse, Sire Malgrin le Chevalier Noyé, le Colosse
  de Givre, Ysolde l'Incandescente et Aldric IV, le Roi sans Aube.
- **Progression** : niveaux et attributs, équipement (18 armes, 4 boucliers, 7 tenues complètes),
  amélioration à la forge, marchands, autels de repos et voyage rapide, deux fins.
- **Création de personnage** : 50 déformations du corps et du visage, coiffures, barbes, couleurs,
  peintures de guerre, cicatrices, voix, origines.
- **Rendu** : HDR, ombres en cascade, ombres du relief et des nuages, SSAO, rayons crépusculaires, bloom,
  brouillard de hauteur, cycle jour/nuit, météo, herbe et végétation instanciées, résolution dynamique.
- **Son** : musique, ambiances et bruitages synthétisés en temps réel (Web Audio).

## Organisation

| Dossier | Rôle |
|---|---|
| `src/` | le jeu : moteur de rendu (`render/`, `world/`), logique (`game/`), interface (`ui/`), son (`audio/`) |
| `assets/` | modèles `.glb`, textures et données du monde produits par Blender |
| `tools/blender/` | scripts Blender (5.1) qui génèrent tous les assets et le monde |
| `vendor/three/` | three.js r187 (licence MIT) |
| `server.mjs` | serveur local sans dépendance |

## Tests

- `tools/ui_test.html` : banc d'essai de l'interface sur un faux jeu ; dans la console : `await __mock.smoke()`.
- `tools/game_smoke.js` : parcours automatique de toutes les fenêtres sur le vrai jeu ; en cours de partie,
  dans la console : `(await import('/tools/game_smoke.js')).run()`.
- Paramètres d'URL de test : `?play=<origine>&nolock=1&t=<heure>&freeze=1&pos=x,z`.
