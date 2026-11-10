// Lore of Valombre: codex, quests, NPCs and their dialogues. All text in French.
// Dialogue nodes are built by functions of the game (g) so they can branch on quests / inventory:
//   node = { text, options: [{ label, go: (g) => node | null }] }      (null / no options = end of conversation)

export const INTRO = [
  "Valombre fut un royaume de lumière. Au cœur de sa citadelle battait l'Astre-Cœur, une étoile tombée du ciel que les rois d'Aubeclair avaient enchâssée dans la pierre.",
  "Le roi Aldric IV, vieillissant, voulut lui arracher l'éternité. Ses alchimistes frappèrent l'Astre. L'Astre se brisa.",
  "Ce fut la Nuit sans Aube. Les Éclats retombèrent sur l'île, et tout ce qu'ils touchèrent — bêtes, hommes, pierres — s'éveilla tordu.",
  "Vous étiez de l'Ordre de la Braise, les Veilleurs des Autels. Vous êtes tombé cette nuit-là. Pourtant, ce matin, les cendres de l'Autel de Hautefeuille se sont remises à rougeoyer… et vous avez ouvert les yeux.",
];

export const CODEX = {
  // ---- Histoire
  nuit: { title: 'La Nuit sans Aube', category: 'Histoire', text: "Il y a onze hivers, l'Astre-Cœur se brisa sous les marteaux des alchimistes royaux. Le ciel au-dessus de la citadelle se fendit d'un éclair blanc, puis le soleil ne se leva pas de trois jours. Quand il revint, les morts du Vieux-Gué marchaient et les loups avaient appris la haine." },
  astre: { title: "L'Astre-Cœur", category: 'Histoire', text: "Une étoile tombée dans la caldeira bien avant les premiers rois. Froide au toucher, elle chantait, dit-on, pour qui savait écouter. Les fondateurs d'Aubeclair la portèrent jusqu'à la citadelle et bâtirent le trône autour d'elle. Tant qu'elle battait, la terre donnait deux moissons l'an." },
  ordre: { title: "L'Ordre de la Braise", category: 'Histoire', text: "Les Veilleurs gardaient les Autels, où une braise de l'Astre était entretenue pour chaque village. Ils juraient de mourir avant elle. La Nuit sans Aube les trouva tous à leur poste. On dit qu'un Autel ranimé se souvient de son Veilleur — et le rappelle." },
  aldric: { title: 'Aldric IV, le Roi sans Aube', category: 'Histoire', text: "Il régna quarante ans avec justice, et un an avec terreur : celui où il comprit qu'il mourrait. Il siège toujours dans la salle du trône, ni vivant ni mort, une main refermée sur le plus gros des Éclats. Il attend l'aube. Il a ordonné qu'elle ne vienne jamais sans lui." },
  eclats: { title: 'Les Éclats', category: 'Histoire', text: "Quatre grands fragments de l'Astre se sont choisi des gardiens : une araignée devenue reine, un chevalier qui refusa de se noyer, un colosse de glace au col du nord, une prêtresse qui prit le feu pour un dieu. Un cinquième est resté dans la main du roi. Réunis, ils peuvent refaire l'Astre — ou l'achever." },
  alchimistes: { title: 'Les alchimistes royaux', category: 'Histoire', text: "Sept savants venus du continent. Ils promirent au roi que l'Astre contenait assez de matins pour un homme éternel. Six moururent dans l'éclair. La septième, Ysolde, sortit des flammes en riant." },
  // ---- Lieux
  hautefeuille: { title: 'Hautefeuille', category: 'Lieux', text: "Le dernier village qui tienne encore marché. Sa palissade est neuve, ses tombes aussi. L'Autel sur la place fut le premier à se rallumer." },
  port: { title: 'Port-Brisants', category: 'Lieux', text: "Des pêcheurs têtus, un phare qu'on rallume chaque soir par habitude. Plus aucun navire ne vient du continent : la mer autour de Valombre ne mène plus nulle part." },
  sombreronce: { title: 'Forêt de Sombreronce', category: 'Lieux', text: "Les bûcherons y entraient en chantant. Aujourd'hui les ronces poussent en une nuit, et les toiles barrent des clairières entières. Au plus profond, quelque chose file." },
  fangemort: { title: 'Marais de Fangemort', category: 'Lieux', text: "Avant la Nuit, c'étaient les rizières du Vieux-Gué. L'eau est montée d'un coup, noire, sans pluie. Les cloches de la chapelle sonnent encore sous la vase, certains soirs." },
  givrelame: { title: 'Pics de Givrelame', category: 'Lieux', text: "Le col du nord était la route des mineurs de Roc-au-Vent. Un gardien de pierre y dormait depuis les premiers rois ; l'Éclat tombé dans sa poitrine l'a réveillé en hiver éternel." },
  calcinees: { title: 'Landes Calcinées', category: 'Lieux', text: "Le plus gros Éclat est retombé là d'où l'Astre était venu : dans la caldeira. La terre y brûle sans flamme. Les fidèles de l'Aube Morte y prient une aube qui ne réchauffe pas." },
  citadelle: { title: "Citadelle d'Aubeclair", category: 'Lieux', text: "Ses portes sont scellées par la volonté du roi. La pierre des remparts garde la trace blanche de l'éclair. Seuls les quatre Éclats réunis peuvent répondre à celui qu'il tient." },
  vieuxgue: { title: 'Le Vieux-Gué', category: 'Lieux', text: "Trois cents âmes. Le marais les a pris dans leur sommeil. Ils se relèvent à la brune, en chemise, et cherchent leurs maisons." },
  rocauvent: { title: 'Roc-au-Vent', category: 'Lieux', text: "Un hameau de mineurs accroché au pied du col. On y forge le meilleur acier de l'île, et on y paie un péage aux trolls quand on ne peut pas faire autrement." },
  refuge: { title: 'Le Refuge des Veilleurs', category: 'Lieux', text: "Une poignée de survivants de l'Ordre campent au cœur de Sombreronce, autour d'un Autel qu'ils n'ont jamais laissé s'éteindre. Ils n'ont plus de maître, seulement un serment." },
  // ---- Créatures
  c_wolf: { title: 'Loups', category: 'Créatures', text: "Ils chassaient les moutons ; ils chassent les bergers. Ceux de la forêt, noirs aux yeux de braise, ne mangent même plus ce qu'ils tuent." },
  c_bandit: { title: 'Écorcheurs', category: 'Créatures', text: "Soldats sans solde, paysans sans terre. Ils dépouillent les voyageurs jusqu'à la peau — d'où leur nom. Leur chef Garrick le Borgne tient un camp à l'est des prés." },
  c_spider: { title: 'Araignées de Sombreronce', category: 'Créatures', text: "De la taille d'un veau. Leur venin épaissit le sang ; un cataplasme d'herbes le chasse. Elles obéissent toutes à la même faim." },
  c_drowned: { title: 'Morts-noyés', category: 'Créatures', text: "Les gens du Vieux-Gué. Lents, patients, innombrables. Ne les laissez pas vous entourer." },
  c_skeleton: { title: 'Squelettes', category: 'Créatures', text: "La garnison du gué, morte à son poste, relevée par l'eau noire. Ils se souviennent de l'escrime." },
  c_wraith: { title: 'Spectres des brumes', category: 'Créatures', text: "Ce qui reste quand le corps a renoncé. L'acier les traverse à peine ; leur cri glace les membres." },
  c_troll: { title: 'Trolls des pics', category: 'Créatures', text: "Plus bêtes que méchants, avant. Leur massue fait trembler le sol : quand le cercle rouge paraît, n'y soyez plus." },
  c_cultist: { title: "Cultistes de l'Aube Morte", category: 'Créatures', text: "Ils ont vu Ysolde sortir du feu et l'ont suivie. Les uns lancent la braise, les autres portent la hache. Tous sourient." },
  c_golem: { title: 'Golems de cendre', category: 'Créatures', text: "Roche de la caldeira animée par une braise. Presque insensibles aux coups légers : frappez fort, ou frappez le cœur quand ils chancellent." },
  c_hollow: { title: 'Chevaliers creux', category: 'Créatures', text: "La garde royale. Il n'y a plus personne dans les armures — seulement la lueur de l'Éclat du roi, et quarante ans de discipline." },
  // ---- Personnages
  p_maelle: { title: 'Sœur Maëlle', category: 'Personnages', text: "Elle balayait la chapelle de Hautefeuille. Quand l'Autel s'est rallumé, elle a été la seule à ne pas s'enfuir. Elle vous a veillé trois nuits." },
  p_arakha: { title: 'Arakha, la Reine Tisseuse', category: 'Personnages', text: "Une araignée de grange. L'Éclat de l'Ombre est tombé dans sa toile. Elle a tissé autour de lui pendant onze ans." },
  p_malgrin: { title: 'Sire Malgrin, le Chevalier Noyé', category: 'Personnages', text: "Capitaine du Vieux-Gué. Il resta debout dans la chapelle tandis que l'eau montait, l'épée levée, jurant de ne pas plier. Il n'a pas plié." },
  p_colosse: { title: 'Le Colosse de Givre', category: 'Personnages', text: "Les fondateurs l'avaient taillé pour garder le col. Il garde toujours. Il ne sait plus contre qui." },
  p_ysolde: { title: "Ysolde l'Incandescente", category: 'Personnages', text: "La septième alchimiste. Elle dit que l'Astre ne s'est pas brisé : qu'il a éclos. Elle attend au bord de la caldeira que le reste suive." },
  p_crocbleme: { title: 'Croc-Blême', category: 'Personnages', text: "Le Grand Alpha des lisières. Blanc comme un os, haut comme un cheval. Les bergers de Hautefeuille ne sortent plus les troupeaux." },
};

// stèles: [codex id, x, z]
export const STELES = [
  ['nuit', -96, 1392], ['ordre', -62, 880], ['astre', 30, 420], ['aldric', -18, 70], ['eclats', 12, -60],
  ['sombreronce', -720, 520], ['p_arakha', -1640, -70], ['fangemort', 1010, 520], ['p_malgrin', 1700, -40], ['vieuxgue', 1215, 300],
  ['givrelame', -560, -1010], ['p_colosse', -330, -1760], ['calcinees', 1090, -600], ['p_ysolde', 1420, -1340], ['alchimistes', 1250, -1050],
  ['port', 1455, 1905], ['p_crocbleme', -800, 800], ['citadelle', -40, 210],
];

const has = (g, id, n = 1) => g.player.count(id) >= n;
const q = (g, id) => g.quests.state(id);
const end = (text) => ({ text, options: [{ label: 'Au revoir.', go: () => null }] });

export const NPCS = {
  maelle: {
    name: 'Sœur Maëlle', role: "Gardienne de l'Autel", place: ['@', -121.5, 1421.5], anim: 'idle_npc', codex: 'p_maelle',
    look: { outfit: 'robe', tintOutfit: '#6b5a48', skin: '#e3c3a6', hair: 'hair_long', hairColor: '#8a8a88', morphs: { feminine: 1, age: 0.7, thin: 0.3 } },
    talk: (g) => {
      if (q(g, 'main') === 'none') return { text: "Vous respirez. Par la Braise… trois nuits que je vous veille, et l'Autel qui rougeoie comme un cœur. Savez-vous seulement qui vous êtes, Veilleur ?", options: [
        { label: "Que s'est-il passé ?", go: () => ({ text: "L'Astre s'est brisé il y a onze hivers. Vous êtes tombé cette nuit-là, avec tout votre Ordre. Mais cet Autel se souvient de vous — et il vous a rappelé. Il doit y avoir une raison.", options: [
          { label: 'Laquelle ?', go: (g2) => { g2.quests.start('main'); return { text: "Quatre Éclats de l'Astre dorment sur l'île, chacun gardé par ce qu'il a perverti. Le cinquième est dans la main du roi, à la citadelle. Tant qu'ils sont séparés, le matin ne reviendra pas vraiment. Allez d'abord à la Croisée, au nord : rallumez l'Autel. Chaque braise ranimée est un endroit où vous ne mourrez pas tout à fait.", options: [{ label: "J'irai.", go: () => null }] }; } }] }) }] };
      if (g.player.data.shards.length >= 4 && !g.flag('maelle_gate')) { g.setFlag('maelle_gate'); return end("Quatre… vous les avez tous. Je les sens d'ici, ils cherchent leur frère. La Porte Royale vous obéira maintenant. Veilleur… quoi que vous décidiez là-haut, décidez-le pour les vivants."); }
      return { text: "L'Autel brûle tant que vous marchez. Reposez-vous près de lui : vos fioles s'y remplissent, vos forces aussi — mais ce que vous avez abattu se relève. Rien ne dort vraiment, ici.", options: [
        { label: 'Parlez-moi des Éclats.', go: () => end("L'Ombre est dans la forêt, à l'ouest. Les Eaux, dans le marais de l'est. Le Givre, au col du nord. La Cendre, dans la caldeira. Commencez par où vous voudrez ; mais la forêt est la moins cruelle.") },
        { label: 'Au revoir.', go: () => null }] };
    },
  },
  hildegarde: {
    name: 'Hildegarde', role: 'Forgeronne', place: ['hautefeuille', 'forge'], anim: 'work_hammer', smith: true,
    look: { outfit: 'leather', skin: '#c79a78', hair: 'hair_ponytail', hairColor: '#5a3a22', morphs: { feminine: 1, muscular: 0.8, shoulder_width: 0.4 } },
    stock: [['iron_sword', 1], ['hatchet', 1], ['mace', 1], ['dagger', 1], ['wood_shield', 1], ['iron_shield', 1], ['leather_head', 1], ['leather_chest', 1], ['leather_legs', 1], ['whetstone', 6], ['steel_shard', 3]],
    talk: (g) => ({ text: q(g, 'smith') === 'done' ? "Votre lame tient ? Bien. Revenez quand elle aura soif." : "Du fer, j'en ai. De l'acier, plus depuis que le col est fermé. Qu'est-ce qu'il vous faut ?", options: [
      { label: 'Voir vos marchandises.', go: (g2) => { g2.openShop('hildegarde'); return null; } },
      { label: 'Améliorer mon équipement.', go: (g2) => { g2.openSmith(); return null; } },
      ...(q(g, 'smith') === 'none' ? [{ label: "Vous manquez d'acier ?", go: (g2) => { g2.quests.start('smith'); return end("Rapportez-moi trois éclats d'acier — les Écorcheurs en ont plein les poches, c'est le mien qu'ils ont volé. Je vous forgerai une vraie épée."); } }] : []),
      ...(q(g, 'smith') === 'active' && has(g, 'steel_shard', 3) ? [{ label: "Voici trois éclats d'acier.", go: (g2) => { g2.player.removeItem('steel_shard', 3); g2.quests.complete('smith'); return end("Ça, c'est de l'acier de Roc-au-Vent. Tenez : je l'avais gardée pour quelqu'un qui en ferait bon usage."); } }] : []),
      { label: 'Au revoir.', go: () => null }] }),
  },
  ysabeau: {
    name: 'Ysabeau', role: 'Marchande', place: ['hautefeuille', 'stall'], anim: 'idle_npc',
    look: { outfit: 'peasant', tintOutfit: '#7a4a3a', skin: '#e0b896', hair: 'hair_braid', hairColor: '#b8452a', morphs: { feminine: 1, heavy: 0.3 } },
    stock: [['bread', 10], ['dried_meat', 8], ['herb_poultice', 6], ['frost_salve', 4], ['whetstone', 4], ['vigor_elixir', 3], ['ember_bomb', 4], ['return_charm', 2], ['peasant_chest', 1], ['peasant_legs', 1]],
    talk: (g) => ({ text: "Du pain, des herbes, de quoi tenir un jour de plus. C'est tout ce que je vends, et c'est déjà beaucoup.", options: [
      { label: 'Voir vos marchandises.', go: (g2) => { g2.openShop('ysabeau'); return null; } },
      ...(q(g, 'silk') === 'none' ? [{ label: 'Besoin de quelque chose ?', go: (g2) => { g2.quests.start('silk'); return end("De la soie d'araignée. Cinq pelotes. Rien ne recoud une plaie comme ça, et plus personne n'ose aller en chercher. Je paie bien."); } }] : []),
      ...(q(g, 'silk') === 'active' && has(g, 'spider_silk', 5) ? [{ label: 'Voici cinq pelotes de soie.', go: (g2) => { g2.player.removeItem('spider_silk', 5); g2.quests.complete('silk'); return end("Noire et solide. Vous venez de sauver plus de monde que vous ne croyez. Prenez ceci — on en verse sur les Autels."); } }] : []),
      { label: 'Au revoir.', go: () => null }] }),
  },
  bertrand: {
    name: 'Bertrand', role: 'Berger', place: ['hautefeuille', -22, 16], anim: 'idle_npc',
    look: { outfit: 'peasant', skin: '#c9a184', hair: 'hair_medium', hairColor: '#6b4728', beard: 'beard_full', morphs: { age: 0.5 } },
    talk: (g) => {
      const s = q(g, 'wolf');
      if (s === 'none') return { text: "Dix-sept bêtes en un mois. Et pas mangées : ouvertes, laissées là. C'est le blanc. Croc-Blême. Il a sa tanière à la lisière, passé le pont de pierre.", options: [
        { label: "Je m'en charge.", go: (g2) => { g2.quests.start('wolf'); return end("Rapportez-moi son croc, que je dorme. Suivez la sente après le pont : elle mène droit chez lui."); } }, { label: 'Pas maintenant.', go: () => null }] };
      if (s === 'active' && has(g, 'wolf_fang')) return { text: "Ce croc… long comme ma main. Alors c'est fait.", options: [{ label: 'Il ne tuera plus.', go: (g2) => { g2.player.removeItem('wolf_fang', 1); g2.quests.complete('wolf'); return end("Prenez ça. C'était à mon fils ; il n'en a plus l'usage, et vous, si."); } }] };
      return end(s === 'done' ? "Les brebis sont ressorties ce matin. Merci, Veilleur." : "La sente après le pont de pierre. Prenez garde : il ne chasse jamais seul.");
    },
  },
  odon: {
    name: 'Capitaine Odon', role: 'Milice de Hautefeuille', place: ['hautefeuille', 'gate'], anim: 'idle_npc',
    look: { outfit: 'chain', weapon: 'iron_sword', skin: '#b98d6c', hair: 'hair_crop', hairColor: '#2b1d14', beard: 'beard_short', morphs: { muscular: 0.5, jaw_width: 0.4 } },
    talk: (g) => {
      const s = q(g, 'bandits');
      if (s === 'none') return { text: "Un Veilleur. Je croyais vos pareils tous morts. Tant mieux : j'ai douze miliciens, et Garrick le Borgne a trente Écorcheurs à une lieue d'ici.", options: [
        { label: 'Où est son camp ?', go: (g2) => { g2.quests.start('bandits'); return end("À l'est, derrière les collines, une palissade. Tuez Garrick, les autres se disperseront. Rapportez-moi sa chevalière."); } }, { label: 'Pas maintenant.', go: () => null }] };
      if (s === 'active' && has(g, 'garrick_ring')) return { text: "Sa chevalière. Volée au vieux bailli, celle-là aussi.", options: [{ label: 'Le camp est à vous.', go: (g2) => { g2.player.removeItem('garrick_ring', 1); g2.quests.complete('bandits'); return end("La milice vous doit une fière chandelle. Prenez cet écu ; il a mieux servi que son dernier porteur."); } }] };
      return end(s === 'done' ? "La route du port est rouverte. On vous le doit." : "Le camp est à l'est, passé la croisée des chemins. Garrick porte une cognée ; ne la laissez pas retomber sur vous.");
    },
  },
  garin: {
    name: 'Garin', role: 'Aubergiste', place: ['hautefeuille', 'tavern'], anim: 'idle_npc',
    look: { outfit: 'peasant', tintOutfit: '#5a4a3a', skin: '#d6a98a', hair: 'hair_bald', hairColor: '#47301f', beard: 'mustache', morphs: { heavy: 0.8, belly: 0.8 } },
    stock: [['bread', 12], ['dried_meat', 10], ['vigor_elixir', 4]],
    talk: (g) => ({ text: "Entrez, entrez — enfin, restez dehors, il fait meilleur. Qu'est-ce que ce sera ?", options: [
      { label: 'À manger.', go: (g2) => { g2.openShop('garin'); return null; } },
      { label: 'Des nouvelles ?', go: () => end(["On dit que le phare de Port-Brisants s'est éteint. Mauvais signe : le vieux Yvain ne l'a jamais laissé s'éteindre.", "Un colporteur jure avoir vu de la lumière dans le marais. Bleue. Elle marchait.", "Les gens de Roc-au-Vent paient un péage à des trolls, maintenant. En moutons. Bientôt en enfants, vous verrez.", "Dans la forêt, les Veilleurs tiendraient encore un camp. Si vous êtes des leurs, ils voudront vous voir."][Math.floor(Math.random() * 4)]) },
      { label: 'Au revoir.', go: () => null }] }),
  },
  yvain: {
    name: 'Yvain', role: 'Gardien du phare', place: ['port_brisants', 6, 4], anim: 'idle_npc',
    look: { outfit: 'peasant', tintOutfit: '#3a4a5a', skin: '#c9a184', hair: 'hair_medium', hairColor: '#d9d6cf', beard: 'beard_long', morphs: { age: 1, thin: 0.4 } },
    talk: (g) => {
      const s = q(g, 'lighthouse');
      if (s === 'none') return { text: "Quarante ans que j'allume ce feu. Et voilà que mes jambes ne montent plus. Si le phare reste noir, ceux de la mer croiront qu'il n'y a plus personne.", options: [
        { label: 'Je le rallumerai.', go: (g2) => { g2.quests.start('lighthouse'); return end("Le brasero est tout en haut, mais la mèche descend jusqu'au pied de la tour. Approchez-en une flamme. Et… méfiez-vous de la grève : la marée ramène des choses."); } }, { label: 'Pas maintenant.', go: () => null }] };
      if (s === 'active' && g.flag('lighthouse_lit')) return { text: "Il brûle ! Regardez-le… On le voit du large, vous savez. On le verra.", options: [{ label: "Qu'il brûle longtemps.", go: (g2) => { g2.quests.complete('lighthouse'); return end("Tenez. Des plumes de retour — les marins en nouaient au mât. Elles vous ramèneront à un Autel, où que vous soyez."); } }] };
      return end(s === 'done' ? "Chaque soir je le regarde. Merci." : "Le pied de la tour, au bout de la jetée de pierre. Une flamme suffit.");
    },
  },
  melisande: {
    name: 'Mélisande', role: 'Poissonnière', place: ['port_brisants', 'stall'], anim: 'idle_npc',
    look: { outfit: 'peasant', tintOutfit: '#4a5a4a', skin: '#b98d6c', hair: 'hair_topknot', hairColor: '#17120f', morphs: { feminine: 1, muscular: 0.3 } },
    stock: [['dried_meat', 12], ['bread', 6], ['herb_poultice', 5], ['frost_salve', 5], ['return_charm', 2]],
    talk: () => ({ text: "Du séché, du salé, du fumé. Le frais, c'est fini : on ne sort plus au large.", options: [{ label: 'Voir vos marchandises.', go: (g2) => { g2.openShop('melisande'); return null; } }, { label: 'Au revoir.', go: () => null }] }),
  },
  tancrede: {
    name: 'Tancrède', role: 'Veilleur blessé', place: ['refuge', 4, 3], anim: 'idle_npc',
    look: { outfit: 'plate', skin: '#a67855', hair: 'hair_short', hairColor: '#8f8f8f', beard: 'beard_short', morphs: { age: 0.6, muscular: 0.5 } },
    stock: [['steel_sword', 1], ['war_axe', 1], ['claymore', 1], ['chain_head', 1], ['chain_chest', 1], ['chain_legs', 1], ['watcher_shield', 1], ['herb_poultice', 6]],
    talk: (g) => {
      const s = q(g, 'letter');
      const opts = [{ label: "Voir l'arsenal du refuge.", go: (g2) => { g2.openShop('tancrede'); return null; } }];
      if (s === 'none') opts.push({ label: 'Que puis-je faire ?', go: (g2) => { g2.quests.start('letter'); g2.player.addItem('old_letter', 1); return end("Cette lettre. Je la porte depuis la Nuit, pour frère Anselme, à Roc-au-Vent. Ma jambe ne passera plus le col. Portez-la. C'est le dernier ordre de notre Grand-Veilleur."); } });
      opts.push({ label: "Parlez-moi de la Reine.", go: () => end("Arakha. Elle est à l'ouest, au bout de la sente, là où les arbres sont blancs de toile. Elle crache, elle bondit, et quand elle se cabre, sa couvée arrive. Tuez les petites d'abord.") }, { label: 'Au revoir.', go: () => null });
      return { text: s === 'done' ? "Anselme a la lettre. Alors l'Ordre peut mourir tranquille… ou revivre. Ça dépend de vous, maintenant." : "Un frère ! Vivant ! Approchez du feu. Nous sommes six. Nous étions quatre cents.", options: opts };
    },
  },
  colin: {
    name: 'Colin', role: 'Éclaireur', place: ['refuge', -5, -2], anim: 'idle_npc',
    look: { outfit: 'leather', skin: '#dcae8c', hair: 'hair_short', hairColor: '#a9713a', morphs: { thin: 0.5 } },
    talk: () => end(["Les araignées n'aiment pas le feu. Une braise vive au milieu d'une couvée, et vous verrez.", "Un coup paré au bon moment fait chanceler n'importe qui. Levez la garde juste avant l'impact, pas avant.", "Le souffle, c'est la vie. Ne videz jamais la barre verte : gardez de quoi rouler.", "Verrouillez une cible et tournez autour. Les gros frappent droit devant eux."][Math.floor(Math.random() * 4)]),
  },
  anselme: {
    name: 'Frère Anselme', role: 'Archiviste de la Braise', place: ['roc_au_vent', 5, -3], anim: 'idle_npc',
    look: { outfit: 'robe', tintOutfit: '#3a3a44', skin: '#e8c2a5', hair: 'hair_bald', hairColor: '#d9d6cf', beard: 'beard_long', morphs: { age: 1, thin: 0.6 } },
    talk: (g) => {
      const s = q(g, 'letter');
      if (s === 'active' && has(g, 'old_letter')) return { text: "Ce sceau… le Grand-Veilleur. Donnez.", options: [{ label: 'De la part de Tancrède.', go: (g2) => { g2.player.removeItem('old_letter', 1); g2.quests.complete('letter'); g2.discoverCodex('ordre'); return { text: "« Si l'Astre tombe, que le dernier d'entre nous choisisse : le refaire, et rendre au roi son éternité avec le matin — ou briser le dernier Éclat, et rendre aux hommes des aubes qui ne durent qu'un jour. » … C'est à vous qu'il écrivait. Prenez le pavois de l'Ordre. Et pardonnez-nous de vous laisser ce choix.", options: [{ label: 'Je choisirai.', go: () => null }] }; } }] };
      return { text: "Les archives de l'Ordre tiennent dans cette besace. Onze hivers de notes sur ce qui nous est arrivé. Demandez.", options: [
        { label: 'Le Colosse ?', go: () => end("Un gardien des premiers rois. Ses coups gèlent. Restez dans son dos, fuyez les cercles, et quand la glace pleut, ne cessez pas de courir.") },
        { label: 'Le roi ?', go: () => end("Aldric n'est pas fou. C'est pire : il a raison de sa peur. Il tient le dernier Éclat. Sans les quatre autres, vous ne passerez même pas sa porte.") },
        { label: 'Au revoir.', go: () => null }] };
    },
  },
  ermeline: {
    name: 'Ermeline', role: 'Doyenne des mineurs', place: ['roc_au_vent', 'stall'], anim: 'idle_npc',
    look: { outfit: 'leather', tintOutfit: '#5a5048', skin: '#c7b6a8', hair: 'hair_braid', hairColor: '#d9d6cf', morphs: { feminine: 1, age: 0.9, heavy: 0.3 } },
    stock: [['steel_sword', 1], ['morningstar', 1], ['great_axe', 1], ['war_hammer', 1], ['plate_head', 1], ['plate_chest', 1], ['plate_legs', 1], ['steel_shard', 6], ['frost_salve', 8], ['dried_meat', 8]],
    talk: (g) => {
      const s = q(g, 'troll');
      const opts = [{ label: 'Voir vos marchandises.', go: (g2) => { g2.openShop('ermeline'); return null; } }];
      if (s === 'none') opts.push({ label: 'On parle de trolls ?', go: (g2) => { g2.quests.start('troll'); return end("Deux, sur la route du col. Ils prennent un mouton par semaine. On n'a plus de moutons. Tuez-les, et l'acier de Roc-au-Vent sera à moitié prix pour vous… façon de parler. Je vous donnerai mieux."); } });
      if (s === 'active' && g.quests.counter('troll') >= 2) opts.push({ label: 'Les deux trolls sont morts.', go: (g2) => { g2.quests.complete('troll'); return end("Deux ! Seul ! Tenez : ça vient du fond de la mine, de l'endroit où on ne creuse plus. Posez-le sur un Autel."); } });
      opts.push({ label: 'Au revoir.', go: () => null });
      return { text: "Roc-au-Vent n'a plus que son acier et sa mauvaise humeur. Vous voulez lequel ?", options: opts };
    },
  },
  ermite: {
    name: "L'Ermite des cendres", role: 'Ancien cultiste', place: ['@', 1105, -545], anim: 'idle_npc',
    look: { outfit: 'robe', tintOutfit: '#4a3a30', skin: '#9c8a80', hair: 'hair_long', hairColor: '#8f8f8f', beard: 'beard_long', morphs: { age: 1, thin: 0.8 } },
    stock: [['ember_bomb', 10], ['frost_salve', 6], ['vigor_elixir', 4], ['astral_fragment', 1], ['robe_head', 1], ['robe_chest', 1], ['robe_legs', 1]],
    talk: () => ({ text: "J'ai prié avec eux. J'ai vu Ysolde marcher sur la lave. Puis j'ai vu ce qu'elle faisait de ceux qui doutaient. Maintenant je vends du feu à ceux qui vont l'éteindre.", options: [
      { label: 'Voir vos marchandises.', go: (g2) => { g2.openShop('ermite'); return null; } },
      { label: 'Comment la vaincre ?', go: () => end("Elle se déplace dans un souffle de braise et frappe de loin. Quand les colonnes de feu s'annoncent, vous avez un battement de cœur. Collez-la : elle déteste ça.") },
      { label: 'Au revoir.', go: () => null }] }),
  },
};

// quest definitions. step: { text, done: (g, quest) => bool }
export const QUESTS = {
  main: { title: "Les Éclats de l'Aube", main: true, desc: "L'Autel de Hautefeuille vous a rappelé d'entre les morts. Quatre Éclats de l'Astre-Cœur sont dispersés sur Valombre ; le cinquième est dans la main du roi.",
    steps: [
      { text: "Embraser l'Autel de la Croisée, au nord de Hautefeuille", done: (g) => g.shrineFound('s_croisee') },
      { text: "Éclat de l'Ombre — vaincre Arakha dans la forêt de Sombreronce", done: (g) => g.flag('boss_spider') },
      { text: 'Éclat des Eaux — vaincre le Chevalier Noyé dans le marais de Fangemort', done: (g) => g.flag('boss_knight') },
      { text: 'Éclat du Givre — vaincre le Colosse au col de Givrelame', done: (g) => g.flag('boss_colossus') },
      { text: "Éclat de Cendre — vaincre Ysolde dans la caldeira", done: (g) => g.flag('boss_priestess') },
      { text: 'Franchir la Porte Royale de la citadelle', done: (g) => g.flag('gate_open') },
      { text: 'Affronter le Roi sans Aube', done: (g) => g.flag('boss_king') },
    ], reward: { xp: 0 }, marker: (g) => g.mainMarker() },
  wolf: { title: 'La bête des lisières', desc: "Croc-Blême, le Grand Alpha, massacre les troupeaux de Hautefeuille. Sa tanière est à la lisière de Sombreronce, après le pont de pierre.",
    steps: [{ text: 'Tuer Croc-Blême dans sa tanière', done: (g) => g.flag('boss_wolf') }, { text: 'Rapporter son croc à Bertrand', done: (g, s) => s === 'done' }], reward: { xp: 400, gold: 150, items: [['leather_chest', 1], ['leather_legs', 1]] }, poi: 'boss_wolf', npc: 'bertrand' },
  bandits: { title: 'Les Écorcheurs', desc: "Garrick le Borgne et sa bande rançonnent la route du port depuis un camp à l'est des prés.",
    steps: [{ text: 'Tuer Garrick le Borgne au camp des Écorcheurs', done: (g) => g.flag('garrick_dead') }, { text: 'Rapporter sa chevalière au capitaine Odon', done: (g, s) => s === 'done' }], reward: { xp: 500, gold: 200, items: [['iron_shield', 1]] }, poi: 'camp_ecorcheurs', npc: 'odon' },
  smith: { title: "L'acier de Roc-au-Vent", desc: "Hildegarde manque d'acier depuis que le col est fermé. Les Écorcheurs lui ont volé ses réserves.",
    steps: [{ text: "Rapporter 3 éclats d'acier à Hildegarde", done: (g, s) => s === 'done' }], reward: { xp: 300, items: [['steel_sword', 1]] }, npc: 'hildegarde' },
  silk: { title: 'Soie noire', desc: "Ysabeau a besoin de soie d'araignée pour recoudre les blessés du village.",
    steps: [{ text: "Rapporter 5 soies d'araignée à Ysabeau", done: (g, s) => s === 'done' }], reward: { xp: 350, gold: 180, items: [['amber_sap', 1]] }, npc: 'ysabeau' },
  letter: { title: 'La lettre du Veilleur', desc: "Tancrède porte depuis onze ans le dernier ordre du Grand-Veilleur, destiné à frère Anselme de Roc-au-Vent.",
    steps: [{ text: 'Porter la lettre scellée à frère Anselme, à Roc-au-Vent', done: (g, s) => s === 'done' }], reward: { xp: 900, items: [['watcher_shield', 1]] }, poi: 'roc_au_vent', npc: 'anselme' },
  lighthouse: { title: 'Le feu des Brisants', desc: "Le phare de Port-Brisants s'est éteint. Le vieux Yvain ne peut plus monter l'allumer.",
    steps: [{ text: 'Rallumer le phare de Port-Brisants', done: (g) => g.flag('lighthouse_lit') }, { text: 'Retourner voir Yvain', done: (g, s) => s === 'done' }], reward: { xp: 350, gold: 120, items: [['return_charm', 2]] }, poi: 'port_brisants', npc: 'yvain' },
  troll: { title: 'Le péage du col', desc: 'Deux trolls rançonnent la route entre Roc-au-Vent et le col de Givrelame.', count: 2, countKill: 'troll',
    steps: [{ text: 'Tuer les trolls du col (2)', done: (g, s, q2) => (q2.n || 0) >= 2 }, { text: 'Retourner voir Ermeline', done: (g, s) => s === 'done' }], reward: { xp: 1200, gold: 300, items: [['ember_seed', 1]] }, poi: 'roc_au_vent', npc: 'ermeline' },
};

export const ENDINGS = {
  reforge: { title: "L'Aube éternelle", text: ["Vous posez les quatre Éclats contre celui du roi. L'Astre se referme, froid, parfait.", "Le soleil se lève sur Valombre et ne se couche plus. Les moissons reviennent. Les morts restent couchés.", "Dans la salle du trône, Aldric IV ouvre les yeux. Il sourit. Il a tout son temps, désormais.", "Vous, vous avez tenu votre serment : la Braise ne s'éteindra jamais."] },
  shatter: { title: 'Le premier matin', text: ["Votre lame s'abat sur le dernier Éclat. Il n'y a pas d'éclair, cette fois. Seulement un soupir.", "Les Autels s'éteignent un à un. Vous sentez la braise qui vous tenait debout pâlir avec eux.", "À l'est, au-dessus de la mer, le ciel rosit. Une aube ordinaire. Elle ne durera qu'un jour.", "À Hautefeuille, sœur Maëlle sort sur le seuil de la chapelle et regarde le soleil se lever. Elle sait."] },
};
