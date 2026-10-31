# -*- coding: utf-8 -*-
"""Builder script to generate the 192-item tiered catalog, updated loot.py, and locale strings."""

# Define items data: (id, name_en, name_es, desc_en, desc_es, slot, tier, req_class, hp, atk, def_, spd, crit, weapon_type, on_hit_status, on_hit_chance, immune_statuses)

ITEMS_DATA = [
    # =========================================================================
    # TIER 1 (ACT 1)
    # =========================================================================

    # --- MAIN_HAND Tier 1 ---
    # Universal
    ("travelers_shortsword", "Traveler's Shortsword", "Espada Corta de Viajero", "A balanced, reliable steel blade.", "Una hoja equilibrada y fiable de acero.", "MAIN_HAND", 1, None, 0, 5, 0, 1, 0.0, "ONE_HANDED", None, 0.0, []),
    ("hunting_spear", "Hunting Spear", "Lanza de Cazador", "A sharp ash spear with good reach.", "Lanza afilada de fresno con buen alcance.", "MAIN_HAND", 1, None, 0, 6, 0, 0, 0.03, "ONE_HANDED", None, 0.0, []),
    # Warrior
    ("bronze_sword", "Iron Broadsword", "Espada Ancha de Hierro", "Solid martial blade with sturdy crossguard.", "Espada marcial robusta con cruceta firme.", "MAIN_HAND", 1, "warrior", 0, 6, 2, 0, 0.0, "ONE_HANDED", None, 0.0, []),
    ("vanguard_cleaver", "Vanguard Cleaver", "Machete de Vanguardia", "Heavy iron cleaver built for chopping strikes.", "Machete pesado de hierro pensado para tajos profundos.", "MAIN_HAND", 1, "warrior", 10, 7, 0, -1, 0.0, "ONE_HANDED", None, 0.0, []),
    # Rogue
    ("worn_dagger", "Bandit Dirk", "Daga de Bandido", "Light and swift dagger with a keen edge.", "Daga ligera y veloz con filo penetrante.", "MAIN_HAND", 1, "rogue", 0, 5, 0, 2, 0.04, "ONE_HANDED", None, 0.0, []),
    ("serrated_stiletto", "Serrated Stiletto", "Estilete Dentado", "Narrow thrusting dagger designed for critical punctures.", "Estilete estrecho disenado para incisiones criticas.", "MAIN_HAND", 1, "rogue", 0, 6, 0, 0, 0.06, "ONE_HANDED", None, 0.0, []),
    # Mage
    ("gnarled_wand", "Apprentice Wand", "Varita de Aprendiz", "Channeled yew wand that sparks with arcane hum.", "Varita de tejo canalizada que vibra con energia arcana.", "MAIN_HAND", 1, "mage", 0, 6, 0, 1, 0.0, "WAND", None, 0.0, []),
    ("oak_focus_staff", "Oak Focus Staff", "Baston Foco de Roble", "Sturdy oak stave grounding magical energies.", "Baston resistente de roble que asienta la magia.", "MAIN_HAND", 1, "mage", 5, 7, 0, 0, 0.0, "TWO_HANDED", None, 0.0, []),

    # --- OFF_HAND Tier 1 ---
    # Universal
    ("wooden_round_shield", "Wooden Round Shield", "Escudo Redondo de Madera", "Reinforced oak planks bound by iron.", "Tablones de roble reforzados con zunchos de hierro.", "OFF_HAND", 1, None, 10, 0, 2, 0, 0.0, "SHIELD", None, 0.0, []),
    ("surveyors_lantern", "Surveyor's Lantern", "Farol de Explorador", "Illuminates blind spots and hastens footwork.", "Ilumina puntos ciegos y agiliza las maniobras.", "OFF_HAND", 1, None, 0, 1, 0, 2, 0.0, None, None, 0.0, []),
    # Warrior
    ("bronze_shield", "Iron Kite Shield", "Escudo Cometa de Hierro", "Broad heater shield providing total flank cover.", "Escudo protector ancho que cubre los flancos.", "OFF_HAND", 1, "warrior", 15, 0, 3, -1, 0.0, "SHIELD", None, 0.0, []),
    ("spiked_targe", "Spiked Targe", "Broquel con Pua", "Round buckler bearing a brutal central counter-spike.", "Escudo pequeno con pua central punzante.", "OFF_HAND", 1, "warrior", 0, 2, 2, 0, 0.0, "SHIELD", None, 0.0, []),
    # Rogue
    ("rusty_parrying_dirk", "Parrying Dagger", "Daga de Parada", "Specialized off-hand dagger for intercepting incoming strikes.", "Daga disenada para desviar y bloquear estocadas.", "OFF_HAND", 1, "rogue", 0, 2, 0, 2, 0.05, "ONE_HANDED", None, 0.0, []),
    ("thiefs_handwraps", "Thief's Weighted Handwraps", "Guanteletes Lastrados de Ladron", "Lead-lined straps enhancing attack tempo.", "Tiras de cuero reforzadas para acelerar el ritmo de ataque.", "OFF_HAND", 1, "rogue", 0, 1, 0, 3, 0.0, None, None, 0.0, []),
    # Mage
    ("tattered_grimoire", "Tattered Spellbook", "Grimorio Roto", "Worn leather tome inscribed with starter incantations.", "Tomo de cuero gastado con formulas elementales.", "OFF_HAND", 1, "mage", 0, 3, 0, 0, 0.04, "FOCUS", None, 0.0, []),
    ("glowing_quartz_orb", "Glowing Quartz Orb", "Orbe de Cuarzo Luminoso", "Pulsing crystal creating a mild protective field.", "Cristal brillante que genera un campo protector sutil.", "OFF_HAND", 1, "mage", 15, 2, 0, 0, 0.0, "FOCUS", None, 0.0, []),

    # --- HEAD Tier 1 ---
    # Universal
    ("padded_arming_cap", "Padded Arming Cap", "Cofia Acolchada", "Quilted cap dampening glancing head strikes.", "Gorro acolchado que amortigua impactos.", "HEAD", 1, None, 10, 0, 1, 0, 0.0, None, None, 0.0, []),
    ("scouts_bandana", "Scout's Bandana", "Panuelo de Explorador", "Light fabric band keeping hair and sweat clear.", "Tira de tela ligera para no perder concentracion.", "HEAD", 1, None, 0, 0, 0, 2, 0.03, None, None, 0.0, []),
    # Warrior
    ("bronze_helmet", "Iron Pot Helmet", "Casco de Bacinete de Hierro", "Stout iron helmet with nose guard.", "Yelmo robusto de hierro con proteccion nasal.", "HEAD", 1, "warrior", 12, 0, 2, 0, 0.0, None, None, 0.0, []),
    ("soldiers_sallet", "Soldier's Sallet", "Celada de Soldado", "Aerodynamic helmet balancing vision and protection.", "Celada de infante que equilibra vision y defensa.", "HEAD", 1, "warrior", 8, 1, 2, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("shadow_cowl", "Leather Eye-Patch", "Parche de Cuero del Granuja", "Sharpens instinct and focus on vulnerable seams.", "Agudiza el instinto para hallar puntos debiles.", "HEAD", 1, "rogue", 0, 1, 0, 1, 0.05, None, None, 0.0, []),
    ("shadow_hood_t1", "Shadow Cowl", "Capucha Sombria", "Supple dark cowl concealing facial movement.", "Capucha oscura que oculta las facciones y movimientos.", "HEAD", 1, "rogue", 10, 0, 0, 2, 0.0, None, None, 0.0, []),
    # Mage
    ("apprentice_cowl", "Novice Scholar Hat", "Gorro de Erudito Novato", "Pointed velvet hat worn by aspiring conjurers.", "Gorro conico de terciopelo de aprendices arcanos.", "HEAD", 1, "mage", 0, 2, 1, 0, 0.0, None, None, 0.0, []),
    ("focus_circlet", "Focus Circlet", "Diadema de Enfoque", "Thin silver circlet clarifying mental spellcasting.", "Diadema fina de plata que canaliza el intelecto.", "HEAD", 1, "mage", 8, 2, 0, 0, 0.03, None, None, 0.0, []),

    # --- CHEST Tier 1 ---
    # Universal
    ("reinforced_leather_jerkin", "Reinforced Leather Jerkin", "Jubon de Cuero Reforzado", "Cured leather sewn with defensive metal studs.", "Cuero endurecido con remaches de metal.", "CHEST", 1, None, 15, 0, 2, 0, 0.0, None, None, 0.0, []),
    ("quilted_doublet", "Quilted Doublet", "Jubon Acolchado", "Thick layers of wool providing flexible warmth and guard.", "Capas de lana densa que ofrecen movilidad y abrigo.", "CHEST", 1, None, 12, 0, 1, 1, 0.0, None, None, 0.0, []),
    # Warrior
    ("bronze_chestplate", "Iron Chainmail Hauberk", "Cota de Malla de Hierro", "Interlocking iron rings offering resilient armor.", "Anillas de hierro entrelazadas muy protectoras.", "CHEST", 1, "warrior", 20, 0, 4, -1, 0.0, None, None, 0.0, []),
    ("infantry_breastplate", "Infantry Breastplate", "Peto de Infanteria", "Solid iron pectoral plating with leather fittings.", "Plancha pectoral de hierro que repele estocadas.", "CHEST", 1, "warrior", 15, 1, 3, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("padded_leather_vest", "Duelist's Gambeson", "Gambeson de Duelista", "Fitted quilted vest allowing unhindered weapon flourishes.", "Chaleco acolchado que no estorba las fintas.", "CHEST", 1, "rogue", 12, 1, 1, 2, 0.0, None, None, 0.0, []),
    ("darkweave_vest", "Darkweave Vest", "Chaleco de Trama Oscura", "Light shadowy garment woven for deadly ambushes.", "Prenda oscura confeccionada para emboscadas letales.", "CHEST", 1, "rogue", 10, 0, 0, 2, 0.04, None, None, 0.0, []),
    # Mage
    ("apprentice_robes", "Apprentice Vestments", "Vestiduras de Aprendiz", "Simple robes woven with ambient mana threads.", "Toga simple con filamentos conductores de mana.", "CHEST", 1, "mage", 10, 3, 1, 0, 0.0, None, None, 0.0, []),
    ("runed_weaver_robe", "Runed Weaver Robe", "Tunica de Tejedor Runico", "Enchanted fabric that pulses with faint warding magic.", "Tela encantada que pulsa con proteccion runica.", "CHEST", 1, "mage", 15, 2, 0, 0, 0.02, None, None, 0.0, []),

    # --- LEGS Tier 1 ---
    # Universal
    ("hardened_boots", "Hardened Boots", "Botas Endurecidas", "Sturdy footwear designed for treacherous trails.", "Calzado firme apto para terrenos escarpados.", "LEGS", 1, None, 10, 0, 1, 1, 0.0, None, None, 0.0, []),
    ("travelers_greaves", "Traveler's Greaves", "Grebas de Caminante", "Light plate greaves shielding the shins.", "Grebas ligeras de metal que cubren las tibias.", "LEGS", 1, None, 12, 0, 2, 0, 0.0, None, None, 0.0, []),
    # Warrior
    ("leather_pants", "Iron Plate Greaves", "Grebas Platedas de Hierro", "Heavy iron greaves anchoring the fighter firmly.", "Grebas de hierro pesado que afianzan la postura.", "LEGS", 1, "warrior", 15, 0, 3, 0, 0.0, None, None, 0.0, []),
    ("hobnail_warboots", "Hobnail Warboots", "Botas Claveadas de Combate", "Studded soles providing brutal grip in melee.", "Suelas con clavos para traccion firme en el choque.", "LEGS", 1, "warrior", 10, 1, 2, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("rogue_breeches", "Soft-Sole Stalkers", "Botas de Suela Blanda", "Muffles footfalls to stalk prey unheard.", "Silencia los pasos para acechar presas sin ser detectado.", "LEGS", 1, "rogue", 8, 0, 0, 3, 0.03, None, None, 0.0, []),
    ("fencers_breeches", "Fencer's Breeches", "Calzones de Esgrimista", "Tailored breeches offering seamless footwork.", "Pantalones ceñidos que permiten pasos veloces.", "LEGS", 1, "rogue", 10, 0, 1, 2, 0.0, None, None, 0.0, []),
    # Mage
    ("woven_pantaloons", "Woven Silk Trousers", "Pantalones de Seda Tejida", "Gentle silk trousers providing comfortable spell focus.", "Pantalones suaves de seda que facilitan la concentracion.", "LEGS", 1, "mage", 8, 2, 0, 1, 0.0, None, None, 0.0, []),
    ("mystic_sandals", "Mystic Sandals", "Sandalias Misticas", "Light enameled sandals attuned to leyline pulses.", "Sandalias esmaltadas sintonizadas con lineas ley.", "LEGS", 1, "mage", 12, 0, 1, 0, 0.02, None, None, 0.0, []),

    # --- SHOULDERS Tier 1 ---
    # Universal
    ("leather_mantle", "Leather Mantle", "Manto de Cuero", "Shoulder wrap protecting against scrapes.", "Capa de hombros que resguarda de rozaduras.", "SHOULDERS", 1, None, 8, 0, 1, 1, 0.0, None, None, 0.0, []),
    ("fur_trimmed_capelet", "Fur-Trimmed Capelet", "Esclavina Ribeteada de Piel", "Warm pelt providing solid cushioning.", "Piel calida que amortigua golpes sobre los hombros.", "SHOULDERS", 1, None, 10, 0, 2, 0, 0.0, None, None, 0.0, []),
    # Warrior
    ("iron_pauldrons", "Iron Pauldrons", "Hombreras de Hierro", "Thick curved iron plates covering shoulders.", "Placas curvadas de hierro sobre las articulaciones.", "SHOULDERS", 1, "warrior", 12, 0, 3, 0, 0.0, None, None, 0.0, []),
    ("spiked_spaulders", "Spiked Spaulders", "Espaldares con Puas", "Jagged spaulders punishing close charges.", "Hombreras dentadas que castigan embestidas.", "SHOULDERS", 1, "warrior", 8, 1, 2, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("shadow_shoulderguards", "Shadow Shoulder-Guards", "Hombreras Sombrias", "Light boiled leather pads that do not snag.", "Piezas de cuero cocido que no entorpecen la capa.", "SHOULDERS", 1, "rogue", 6, 0, 0, 2, 0.03, None, None, 0.0, []),
    ("brawlers_epaulets", "Brawler's Epaulets", "Charreteras de Rufian", "Reinforced shoulders built for brawl lunges.", "Hombros reforzados para cargas cuerpo a cuerpo.", "SHOULDERS", 1, "rogue", 0, 1, 1, 2, 0.0, None, None, 0.0, []),
    # Mage
    ("scholars_stole", "Scholar's Stole", "Estola de Erudito", "Inscribed cloth hanging over the chest and shoulders.", "Tela bordada con formulas que envuelve el cuello.", "SHOULDERS", 1, "mage", 5, 2, 1, 0, 0.0, None, None, 0.0, []),
    ("aether_capelet", "Aether Capelet", "Esclavina de Eter", "Light cape shimmering with elemental trace.", "Capa corta que destella con trazas elementales.", "SHOULDERS", 1, "mage", 0, 3, 0, 0, 0.02, None, None, 0.0, []),

    # --- HANDS Tier 1 ---
    # Universal
    ("padded_gloves", "Padded Gloves", "Guantes Acolchados", "Supple gloves granting firm weapon grip.", "Guantes flexibles que facilitan un agarre firme.", "HANDS", 1, None, 6, 0, 1, 1, 0.0, None, None, 0.0, []),
    ("reinforced_mitts", "Reinforced Mitts", "Mitones Reforzados", "Thick leather gloves with studded knuckles.", "Guantes gruesos de cuero tachonado.", "HANDS", 1, None, 10, 0, 2, 0, 0.0, None, None, 0.0, []),
    # Warrior
    ("leather_gloves", "Iron Gauntlets", "Guanteletes de Hierro", "Articulated iron plates shielding wrists and fingers.", "Laminas de hierro articuladas para las manos.", "HANDS", 1, "warrior", 10, 1, 2, 0, 0.0, None, None, 0.0, []),
    ("grip_wraps", "Grip Wraps", "Bandas de Sujecion", "Rawhide wraps securing weapon purchase.", "Tiras de cuero crudo que mejoran la fuerza del golpe.", "HANDS", 1, "warrior", 5, 2, 1, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("cutpurse_gloves", "Cutpurse Fingerless Gloves", "Guantes sin Dedos de Cortabolsas", "Exposes fingers for lockpicking and swift blade draws.", "Dedos descubiertos para juegos de manos y desenfunde veloz.", "HANDS", 1, "rogue", 0, 1, 0, 2, 0.04, None, None, 0.0, []),
    ("quickdraw_bracers", "Quickdraw Bracers", "Brazales de Reaccion", "Leather wrist-bracers priming instantaneous thrusts.", "Brazales de cuero que agilizan las fintas inmediatas.", "HANDS", 1, "rogue", 0, 0, 0, 3, 0.03, None, None, 0.0, []),
    # Mage
    ("cloth_handwraps", "Channeler's Silk Gloves", "Guantes de Seda del Canalizador", "Conductive silk glove pair focusing spell flow.", "Guantes de seda pura que canalizan las chispas arcanas.", "HANDS", 1, "mage", 0, 3, 0, 1, 0.0, None, None, 0.0, []),
    ("spellscribe_cuffs", "Spellscribe Cuffs", "Manguitos del Amanuense", "Protects wrists during extended casting rituals.", "Protegen los pulsos durante rituales prolongados.", "HANDS", 1, "mage", 0, 2, 1, 0, 0.03, None, None, 0.0, []),

    # --- WAIST Tier 1 ---
    # Universal
    ("leather_belt", "Sturdy Leather Belt", "Cinturon Robusto de Cuero", "A wide utility belt with iron clasp.", "Cinturon de explorador con hebilla de hierro.", "WAIST", 1, None, 10, 0, 1, 0, 0.0, None, None, 0.0, []),
    ("rope_sash", "Rope Sash", "Cinto de Cuerda", "Knotted sash promoting easy body pivoting.", "Faja anudada que no restringe giros repentinos.", "WAIST", 1, None, 0, 0, 0, 1, 0.03, None, None, 0.0, []),
    # Warrior
    ("iron_girdle", "Iron Plated Girdle", "Faja Plateda de Hierro", "Broad belt protecting hips and kidneys.", "Faja ancha con refuerzos para el vientre y caderas.", "WAIST", 1, "warrior", 14, 0, 3, 0, 0.0, None, None, 0.0, []),
    ("war_horn_belt", "War-Horn Belt", "Cinto del Cuerno de Guerra", "Thick belt adorned with warlike brass studs.", "Cinturon grueso con tachones marciales de bronce.", "WAIST", 1, "warrior", 8, 1, 2, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("thiefs_toolbelt", "Thief's Toolbelt", "Cinto de Ganzuas", "Pouches containing oils, lockpicks, and quick-knives.", "Bolsillos pequenos para viales, ganzuas y dardos.", "WAIST", 1, "rogue", 5, 0, 0, 2, 0.04, None, None, 0.0, []),
    ("viper_belt", "Viper Belt", "Cinturon de la Vibora", "Supple snakeskin belt enhancing bodily fluidity.", "Cinturon de piel de serpiente que estiliza el movimiento.", "WAIST", 1, "rogue", 0, 1, 0, 2, 0.02, None, None, 0.0, []),
    # Mage
    ("runic_cord", "Runic Cord", "Cordon Runico", "Braided cord vibrating with defensive wards.", "Cordon trenzado con inscripciones protectoras.", "WAIST", 1, "mage", 8, 3, 0, 0, 0.0, None, None, 0.0, []),
    ("mana_cinch", "Mana-Infused Cinch", "Faja Imbuida de Mana", "Tight cloth cinch circulating spiritual energy.", "Faja que mantiene alineado el flujo magico interior.", "WAIST", 1, "mage", 0, 2, 1, 1, 0.0, None, None, 0.0, []),


    # =========================================================================
    # TIER 2 (ACT 2)
    # =========================================================================

    # --- MAIN_HAND Tier 2 ---
    # Universal
    ("tempered_steel_longsword", "Tempered Steel Longsword", "Mandoble Templado de Acero", "Expertly quenched steel longsword with fine balance.", "Espada larga de acero templado con filo impecable.", "MAIN_HAND", 2, None, 0, 14, 1, 0, 0.05, "ONE_HANDED", None, 0.0, []),
    ("barbed_glaive", "Huntsman's Barbed Glaive", "Guja Barbada de Cazador", "Cruel polearm with barbed blades.", "Arma de asta cruel con cuchillas dentadas.", "MAIN_HAND", 2, None, 15, 15, 0, 2, 0.0, "TWO_HANDED", None, 0.0, []),
    # Warrior
    ("steel_claymore", "Steel Claymore", "Mandoble de Acero", "Massive blade sweeping across the frontline.", "Hoja colosal capaz de quebrar escudos enemigos.", "MAIN_HAND", 2, "warrior", 15, 17, 0, -1, 0.0, "TWO_HANDED", None, 0.0, []),
    ("heavy_war_mace", "Heavy War Mace", "Maza Pesada de Guerra", "Flanged steel mace designed to crush full plate.", "Maza con pestañas de acero que abolla corazas.", "MAIN_HAND", 2, "warrior", 0, 15, 4, 0, 0.04, "ONE_HANDED", None, 0.0, []),
    # Rogue
    ("assassins_dirk", "Assassin's Dirk", "Daga del Asesino", "Balanced weapon intended for lethal throat strikes.", "Arma equilibrada disenada para estocadas mortales.", "MAIN_HAND", 2, "rogue", 0, 13, 0, 5, 0.10, "ONE_HANDED", None, 0.0, []),
    ("venom_stiletto", "Venom-Tipped Stiletto", "Estilete Emponzonado", "Grooved stiletto constantly dripping venom.", "Estilete ranurado que rezuma veneno paralizante.", "MAIN_HAND", 2, "rogue", 0, 14, 0, 3, 0.0, "ONE_HANDED", "poison", 0.25, []),
    # Mage
    ("crystalline_wand", "Crystalline Wand", "Varita Cristalina", "Prismatic core wand intensifying spell impact.", "Varita de nucleo prismatico que intensifica hechizos.", "MAIN_HAND", 2, "mage", 0, 16, 0, 2, 0.06, "WAND", None, 0.0, []),
    ("staff_of_embers", "Staff of Embers", "Baston de Ascuas", "Ever-burning staff igniting foes upon contact.", "Baston igneo perpetuo que calcina al golpear.", "MAIN_HAND", 2, "mage", 15, 15, 0, 0, 0.0, "TWO_HANDED", "burn", 0.25, []),

    # --- OFF_HAND Tier 2 ---
    # Universal
    ("reinforced_heater_shield", "Reinforced Heater Shield", "Escudo Templado de Acero", "Polished steel shield with heraldic rivets.", "Escudo pulido de acero con remaches heraldicos.", "OFF_HAND", 2, None, 25, 0, 5, 0, 0.0, "SHIELD", None, 0.0, []),
    ("alchemists_satchel", "Alchemist's Satchel", "Cartera de Alquimista", "Bandolier of volatile salts granting versatile tactics.", "Bolsa con sales volatiles que favorece la improvisacion.", "OFF_HAND", 2, None, 10, 3, 0, 3, 0.0, None, None, 0.0, []),
    # Warrior
    ("steel_bastion_shield", "Steel Bastion Shield", "Escudo Bastion de Acero", "Massive fortress shield absorbing titanic blows.", "Pared de acero solido que absorbe impactos titanicos.", "OFF_HAND", 2, "warrior", 35, 0, 7, -2, 0.0, "SHIELD", None, 0.0, []),
    ("bladed_spiked_shield", "Bladed Spiked Shield", "Escudo Cortante con Puas", "Off-hand buckler lined with sharpened edges.", "Escudo con hojas laterales para contraataques letales.", "OFF_HAND", 2, "warrior", 15, 6, 4, 0, 0.0, "SHIELD", None, 0.0, []),
    # Rogue
    ("main_gauche", "Main Gauche", "Daga de Guardia", "Exquisite dueling dagger intercepting lethal thrusts.", "Exquisita daga de esgrima que neutraliza estocadas.", "OFF_HAND", 2, "rogue", 0, 5, 3, 4, 0.06, "ONE_HANDED", None, 0.0, []),
    ("steel_buckler", "Steel Buckler", "Broquel de Acero", "Light steel shield engineered for deflections.", "Escudo pequeno y agil que desvia tajos directos.", "OFF_HAND", 2, "rogue", 20, 0, 4, 3, 0.0, "SHIELD", None, 0.0, []),
    # Mage
    ("arcane_grimoire", "Arcane Grimoire", "Grimorio Arcano", "Bound tome containing ancient arcane incantations.", "Tomo encuadernado que rebosa encantamientos milenarios.", "OFF_HAND", 2, "mage", 0, 8, 0, 0, 0.08, "FOCUS", None, 0.0, []),
    ("mirror_ward", "Enchanted Mirror Ward", "Espejo Guardian Encantado", "Silvered ward reflecting incoming hostile spells.", "Placa plateada que dispersa y repele la energia hostil.", "OFF_HAND", 2, "mage", 25, 4, 3, 0, 0.0, "FOCUS", None, 0.0, []),

    # --- HEAD Tier 2 ---
    # Universal
    ("steel_kettle_hat", "Steel Kettle Hat", "Capelina de Acero", "Wide-brimmed helmet deflecting downward blows.", "Yelmo de ala ancha que desvia proyectiles y tajos altos.", "HEAD", 2, None, 20, 0, 4, 0, 0.0, None, None, 0.0, []),
    ("highwaymans_mask", "Highwayman's Mask", "Mascara de Bandolero", "Silk-lined mask keeping gaze sharp and focused.", "Antifaz oscuro que enfoca la mirada en el peligro.", "HEAD", 2, None, 0, 2, 0, 3, 0.06, None, None, 0.0, []),
    # Warrior
    ("full_visor_helm", "Full Visor Helm", "Yelmo con Visera Completa", "Impenetrable steel helmet with slitted eyeholes.", "Casco de placas completas que envuelve la cabeza.", "HEAD", 2, "warrior", 25, 0, 6, 0, 0.0, None, None, 0.0, []),
    ("knights_armet", "Knight's Armet", "Armete de Caballero", "Elegantly forged armet worn by order champions.", "Armete forjado con orgullo para campeones de orden.", "HEAD", 2, "warrior", 20, 3, 4, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("nightstalker_hood", "Nightstalker Hood", "Capucha del Acechador Nocturno", "Shadowy hood blending effortlessly into dim cover.", "Capucha negra tratada para mimetizarse en sombras.", "HEAD", 2, "rogue", 15, 2, 0, 4, 0.07, None, None, 0.0, []),
    ("shadow_mask", "Shadow Mask", "Mascara Sombria", "Leather mask concealing breath and sudden eye turns.", "Mascara de cuero que oculta respiracion y reflejos.", "HEAD", 2, "rogue", 12, 0, 0, 5, 0.08, None, None, 0.0, []),
    # Mage
    ("scholars_pointed_hat", "Scholar's Pointed Cap", "Sombrero Picudo de Sabio", "Starred felt hat sharpening magical cognition.", "Sombrero estrellado que clarifica deducciones magicas.", "HEAD", 2, "mage", 10, 6, 2, 0, 0.0, None, None, 0.0, []),
    ("arcanists_circlet", "Arcanist's Circlet", "Diadema del Arcanista", "Gemmed headpiece gathering ambient mana filaments.", "Corona de gemas que atrae filamentos de mana.", "HEAD", 2, "mage", 0, 7, 0, 2, 0.06, None, None, 0.0, []),

    # --- CHEST Tier 2 ---
    # Universal
    ("brigandine_armor", "Brigandine Armor", "Armadura de Brigantina", "Steel plates riveted inside supple leather.", "Planchas de acero remachadas bajo cuero flexible.", "CHEST", 2, None, 30, 0, 5, 0, 0.0, None, None, 0.0, []),
    ("layered_hauberk", "Layered Maille Hauberk", "Cota de Malla Laminada", "Intertwined rings backed by sturdy gambeson.", "Doble capa de anillas sobre jubon acolchado.", "CHEST", 2, None, 25, 0, 4, 2, 0.0, None, None, 0.0, []),
    # Warrior
    ("steel_cuirass", "Steel Cuirass", "Coraza de Acero", "Heavy breastplate forging an unbroken shield.", "Peto macizo que resiste estocadas directas.", "CHEST", 2, "warrior", 40, 0, 8, -1, 0.0, None, None, 0.0, []),
    ("vanguard_halfplate", "Vanguard Half-Plate", "Media Armadura de Vanguardia", "Molded steel half-suit balancing offense and armor.", "Conjunto de placas frontales que no limita el golpe.", "CHEST", 2, "warrior", 30, 4, 6, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("shadowweave_tunic", "Shadowweave Tunic", "Tunica de Sombras Tejidas", "Dark cloth woven from nightshade gossamer.", "Tela oscura hilada con hebras de belladona.", "CHEST", 2, "rogue", 20, 4, 3, 5, 0.0, None, None, 0.0, []),
    ("fencers_doublet", "Fencer's Doublet", "Jubon de Esgrima", "Tailored doublet designed for quick ripostes.", "Jubon entallado confeccionado para respuestas rapidas.", "CHEST", 2, "rogue", 18, 2, 2, 6, 0.06, None, None, 0.0, []),
    # Mage
    ("spellweaver_robe", "Spellweaver Robe", "Tunica del Tejedor de Hechizos", "Resonant robes amplifying arcane cast power.", "Vestidura resonante que potencia formulas arcanas.", "CHEST", 2, "mage", 20, 8, 3, 2, 0.0, None, None, 0.0, []),
    ("runed_battlerobes", "Runed Battle-Robes", "Tunicas de Combate Runicas", "Heavily fortified robes shielding battle-mages.", "Tunicas con placas internas para magos de combate.", "CHEST", 2, "mage", 30, 6, 4, 0, 0.0, None, None, 0.0, []),

    # --- LEGS Tier 2 ---
    # Universal
    ("steel_greaves", "Steel Greaves", "Grebas de Acero", "Steel shin guards deflecting wild swings.", "Protectores de acero para las canillas.", "LEGS", 2, None, 25, 0, 5, 0, 0.0, None, None, 0.0, []),
    ("reinforced_riding_trousers", "Reinforced Riding Trousers", "Pantalones Reforzados de Jinete", "Sturdy pants allowing agile mounting and dodging.", "Pantalones resistentes con buen margen de evasion.", "LEGS", 2, None, 20, 0, 3, 3, 0.0, None, None, 0.0, []),
    # Warrior
    ("heavy_plate_sabatons", "Heavy Plate Sabatons", "Escarpes Pesados de Placas", "Solid steel boots grounding against charges.", "Botas de placas que afianzan contra arremetidas.", "LEGS", 2, "warrior", 30, 0, 6, 0, 0.0, None, None, 0.0, []),
    ("knightly_greaves", "Knightly Greaves", "Grebas Caballerescas", "Polished steel greaves embossed with battle crests.", "Grebas pulidas grabadas con emblemas de batalla.", "LEGS", 2, "warrior", 25, 2, 5, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("stalker_breeches", "Stalker Breeches", "Calzas de Acechador", "Flexible pants optimized for silent flanking.", "Pantalones flexibles idoneos para flanqueos silenciosos.", "LEGS", 2, "rogue", 15, 2, 0, 6, 0.05, None, None, 0.0, []),
    ("quicksilver_boots", "Quicksilver Boots", "Botas de Azogue", "Enchanted soles lightening body weight.", "Calzado encantado que aligera cada pisada.", "LEGS", 2, "rogue", 12, 0, 2, 7, 0.0, None, None, 0.0, []),
    # Mage
    ("archivists_trousers", "Archivist's Trousers", "Pantalones del Archivista", "Embroidered breeches protecting the caster's footing.", "Calzas bordadas con runas de estabilidad magica.", "LEGS", 2, "mage", 15, 5, 2, 2, 0.0, None, None, 0.0, []),
    ("astral_weft_skirt", "Astral Weft Skirt", "Falda de Urdimbre Astral", "Silk layered skirt humming with astral cadence.", "Falda con capas de seda que oscila con pulso astral.", "LEGS", 2, "mage", 20, 6, 0, 0, 0.03, None, None, 0.0, []),

    # --- SHOULDERS Tier 2 ---
    # Universal
    ("steel_pauldrons", "Steel Pauldrons", "Hombreras de Acero", "Thick shoulder plates deflecting heavy blows.", "Piezas de acero templado que resguardan los hombros.", "SHOULDERS", 2, None, 20, 0, 4, 0, 0.0, None, None, 0.0, []),
    ("hardened_leather_mantle", "Hardened Leather Mantle", "Manto de Cuero Curtido", "Thickened mantle providing mobility and protection.", "Manto de cuero curado que permite balancear armas.", "SHOULDERS", 2, None, 15, 0, 2, 3, 0.0, None, None, 0.0, []),
    # Warrior
    ("tower_guard_spaulders", "Tower Guard Spaulders", "Espaldares de Guardia de la Torre", "Heavy overlapping plates guarding neck and shoulders.", "Laminas gruesas que protegen cuello y clavicula.", "SHOULDERS", 2, "warrior", 25, 0, 6, 0, 0.0, None, None, 0.0, []),
    ("spiked_steel_pauldrons", "Spiked Steel Pauldrons", "Hombreras de Acero con Puas", "Menacing spiked shoulder guards.", "Hombreras con puas que lastiman al impactar.", "SHOULDERS", 2, "warrior", 15, 3, 4, 0, 0.03, None, None, 0.0, []),
    # Rogue
    ("duelists_epaulets", "Duelist's Epaulets", "Charreteras de Duelista", "Lightweight epaulets favoring swift sword pivots.", "Charreteras ligeras que favorecen estocadas precisas.", "SHOULDERS", 2, "rogue", 10, 3, 2, 4, 0.0, None, None, 0.0, []),
    ("assassins_shroud", "Assassin's Shroud", "Manto del Asesino", "Muffled cloth draping over killing shoulders.", "Capa oscura que disimula el desenfunde de hojas cortas.", "SHOULDERS", 2, "rogue", 12, 2, 0, 5, 0.05, None, None, 0.0, []),
    # Mage
    ("mantle_of_sparks", "Mantle of Sparks", "Manto de Chispas", "Crackle of harmless sparks warning away foes.", "Capa chisporroteante que asusta a agresores.", "SHOULDERS", 2, "mage", 10, 6, 2, 0, 0.0, None, None, 0.0, []),
    ("star_woven_shawl", "Star-Woven Shawl", "Chal Tejido con Estrellas", "Gleaming shawl drawing focus from celestial bodies.", "Chal brillante que atrae influjo de cuerpos celestes.", "SHOULDERS", 2, "mage", 0, 7, 0, 3, 0.04, None, None, 0.0, []),

    # --- HANDS Tier 2 ---
    # Universal
    ("steel_plated_mitts", "Steel-Plated Mitts", "Mitones Platedos de Acero", "Rigid gloves protecting fingers from bone-breaks.", "Guantes rigidos que salvan los dedos de fracturas.", "HANDS", 2, None, 20, 0, 4, 0, 0.0, None, None, 0.0, []),
    ("brawler_handwraps", "Brawler Handwraps", "Guantes de Rufian", "Toughened wraps delivering punishing brawling strikes.", "Vendajes endurecidos para peleas encarnizadas.", "HANDS", 2, None, 0, 3, 2, 3, 0.04, None, None, 0.0, []),
    # Warrior
    ("knights_gauntlets", "Knight's Gauntlets", "Guanteletes de Caballero", "Finely articulated plate gauntlets with leather grips.", "Guanteletes de caballero con forro interior de cuero.", "HANDS", 2, "warrior", 20, 3, 4, 0, 0.0, None, None, 0.0, []),
    ("executioners_grips", "Executioner's Grips", "Manoplas del Verdugo", "Heavy leather grips maximizing cleave force.", "Guantes pesados disenados para asestar el tajo final.", "HANDS", 2, "warrior", 10, 4, 2, 0, 0.05, None, None, 0.0, []),
    # Rogue
    ("cutpurse_leather_gloves", "Cutpurse Leather Gloves", "Guantes de Cuero de Rapina", "Supple gloves granting surgical dagger control.", "Guantes flexibles que otorgan precision quirurgica.", "HANDS", 2, "rogue", 0, 3, 0, 4, 0.07, None, None, 0.0, []),
    ("shadowfinger_bracers", "Shadowfinger Bracers", "Brazales de Dedo Sombrio", "Conceals throwing darts and quick-release blades.", "Ocultan dardos y resortes de hojas pequenas.", "HANDS", 2, "rogue", 0, 2, 1, 6, 0.05, None, None, 0.0, []),
    # Mage
    ("sorcerers_silk_gloves", "Sorcerer's Silk Gloves", "Guantes de Seda del Brujo", "Intricate stitchings amplifying spell focus.", "Bordados complejos que expanden el foco de conjuros.", "HANDS", 2, "mage", 0, 6, 0, 2, 0.04, None, None, 0.0, []),
    ("mana_channeling_wraps", "Mana-Channeling Wraps", "Bandas Canalizadoras de Mana", "Tightly bound wraps sustaining intense magical output.", "Tiras de lino que sostienen torrentes de poder arcano.", "HANDS", 2, "mage", 12, 7, 2, 0, 0.0, None, None, 0.0, []),

    # --- WAIST Tier 2 ---
    # Universal
    ("steel_buckled_belt", "Steel-Buckled Belt", "Cinturon con Hebilla de Acero", "Broad leather belt with forged iron reinforcement.", "Cinturon ancho con refuerzos forjados en acero.", "WAIST", 2, None, 22, 0, 4, 0, 0.0, None, None, 0.0, []),
    ("adventurers_utility_sash", "Adventurer's Utility Sash", "Faja de Utilidad del Aventurero", "Multipurpose belt loaded with hooks and pouches.", "Faja utilitaria cargada de enganches y faltriqueras.", "WAIST", 2, None, 15, 0, 2, 3, 0.03, None, None, 0.0, []),
    # Warrior
    ("plated_war_belt", "Plated War-Belt", "Cinto Platedo de Guerra", "Heavy plate-reinforced belt holding plate legs.", "Cinto reforzado con placas para asegurar armaduras.", "WAIST", 2, "warrior", 28, 2, 5, 0, 0.0, None, None, 0.0, []),
    ("girdle_of_the_mountain", "Girdle of the Mountain", "Faja de la Montana", "Stout dwarven belt bolstering core constitution.", "Faja enana que fortalece el centro de gravedad.", "WAIST", 2, "warrior", 35, 0, 6, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("duelists_rapier_frog", "Duelist's Rapier Frog", "Tahalí de Estoque de Duelista", "Secure leather frog balancing off-hand daggers.", "Tahali ajustado que balancea armas accesorias.", "WAIST", 2, "rogue", 0, 3, 2, 4, 0.05, None, None, 0.0, []),
    ("viper_stalker_belt", "Viper Stalker Belt", "Cinturon Acechador de la Vibora", "Padded belt carrying concealed glass poison vials.", "Cinturon acolchado con huecos para viales de veneno.", "WAIST", 2, "rogue", 12, 2, 0, 5, 0.06, None, None, 0.0, []),
    # Mage
    ("runic_sash", "Runic Silk Sash", "Faja de Seda Runica", "Gilded sash inscribed with ancient protection runes.", "Faja de seda bordada con sellos arcanos protectores.", "WAIST", 2, "mage", 15, 7, 2, 0, 0.0, None, None, 0.0, []),
    ("spellbinder_cord", "Spellbinder Cord", "Cordon Encantador", "Braided cord vibrating with heightened casting rhythm.", "Cordon trenzado que acompasa el ritmo de invocacion.", "WAIST", 2, "mage", 0, 8, 0, 2, 0.05, None, None, 0.0, []),


    # =========================================================================
    # TIER 3 (ACT 3)
    # =========================================================================

    # --- MAIN_HAND Tier 3 ---
    # Universal
    ("ancient_sunblade", "Ancient Sunblade", "Hoja Solar Ancestral", "A radiant blade blazing with eternal solar fire.", "Hoja radiante envuelta en llamas solares perennes.", "MAIN_HAND", 3, None, 20, 26, 3, 0, 0.08, "ONE_HANDED", "burn", 0.40, []),
    ("meteorite_cleaver", "Meteorite Cleaver", "Machete de Meteorito", "Heavy cosmic iron cleaver opening bleeding wounds.", "Arma forjada en hierro cosmico que abre heridas sangrantes.", "MAIN_HAND", 3, None, 30, 28, 0, -2, 0.10, "TWO_HANDED", "bleed", 0.40, []),
    # Warrior
    ("worldbreaker_greatsword", "Worldbreaker Greatsword", "Espada Devastadora de Mundos", "Colossal legendary broadsword shattering enemy ranks.", "Espadon legendario colosal que pulveriza defensas.", "MAIN_HAND", 3, "warrior", 35, 34, 8, 0, 0.10, "TWO_HANDED", None, 0.0, []),
    ("doomhammer_ancients", "Doomhammer of the Ancients", "Martillo del Destino Ancestral", "Titan-forged hammer whose impact echoes thunder.", "Martillo forjado por titanes cuyo golpe retumba como trueno.", "MAIN_HAND", 3, "warrior", 0, 30, 12, 5, 0.0, "ONE_HANDED", None, 0.0, []),
    # Rogue
    ("whisper_of_the_void", "Whisper of the Void", "Susurro del Vacio", "Translucent phantom blade piercing through reality.", "Hoja fantasmal que atraviesa sombras y corazas.", "MAIN_HAND", 3, "rogue", 0, 27, 0, 12, 0.25, "ONE_HANDED", None, 0.0, []),
    ("viper_queens_stinger", "Viper Queen's Stinger", "Aguijon de la Reina Vibora", "Dripping stiletto laced with lethal sovereign neurotoxin.", "Aguijon letal impregnado de neurotoxina soberana.", "MAIN_HAND", 3, "rogue", 20, 25, 0, 8, 0.0, "ONE_HANDED", "poison", 0.50, []),
    # Mage
    ("calamity_staff", "Calamity Staff", "Baston de la Calamidad", "Crackles with apocalyptic raw cataclysm energy.", "Baston que chisporrotea con energia pura del apocalipsis.", "MAIN_HAND", 3, "mage", 20, 33, 0, 5, 0.15, "TWO_HANDED", None, 0.0, []),
    ("spire_of_the_archon", "Spire of the Archon", "Aguja del Arconte", "Primordial spire focusing absolute cosmic authority.", "Vara primordial que concentra autoridad cosmica absoluta.", "MAIN_HAND", 3, "mage", 25, 31, 6, 0, 0.10, "TWO_HANDED", None, 0.0, []),

    # --- OFF_HAND Tier 3 ---
    # Universal
    ("aegis_of_the_immortal", "Aegis of the Immortal", "Egida del Inmortal", "Ancient bulwark making the wielder unyielding to stuns.", "Escudo ancestral que vuelve al portador inmune al aturdimiento.", "OFF_HAND", 3, None, 50, 0, 12, 0, 0.0, "SHIELD", None, 0.0, ["stun"]),
    ("relic_of_the_eclipse", "Relic of the Eclipse", "Reliquia del Eclipse", "Celestial duality relic empowering swift deadly strikes.", "Reliquia de dualidad cosmica que acelera los golpes.", "OFF_HAND", 3, None, 20, 8, 0, 10, 0.10, None, None, 0.0, []),
    # Warrior
    ("colossus_tower_bastion", "Colossus Tower Bastion", "Bastion de Torre del Coloso", "Impenetrable slab of living blackstone.", "Muro de roca negra viva practicamente impenetrable.", "OFF_HAND", 3, "warrior", 65, 0, 16, -2, 0.0, "SHIELD", None, 0.0, []),
    ("dreadnought_spiked_shield", "Dreadnought Spiked Shield", "Escudo Acorazado con Puas", "War fortress shield bearing heavy serrated spines.", "Escudo de asedio cubierto de colmillos de acero.", "OFF_HAND", 3, "warrior", 40, 12, 10, 0, 0.05, "SHIELD", None, 0.0, []),
    # Rogue
    ("phantom_parrying_stiletto", "Phantom Parrying Stiletto", "Estilete Espectral de Parada", "Ethereal parrying blade deflecting strikes into mist.", "Daga espectral que desvanece ataques en niebla.", "OFF_HAND", 3, "rogue", 0, 10, 8, 8, 0.15, "ONE_HANDED", None, 0.0, []),
    ("shadow_mirror_buckler", "Shadow Mirror Buckler", "Broquel Espejo de Sombras", "Absorbs incoming force and converts it to agility.", "Absorbe la fuerza enemiga y la transmuta en agilidad.", "OFF_HAND", 3, "rogue", 35, 0, 9, 6, 0.08, "SHIELD", None, 0.0, []),
    # Mage
    ("tome_ancient_cataclysms", "Tome of Ancient Cataclysms", "Tomo de Cataclismos Ancestrales", "Grimoire detailing primordial star eruptions.", "Grimorio que detalla la destruccion de soles antiguos.", "OFF_HAND", 3, "mage", 0, 16, 4, 0, 0.15, "FOCUS", None, 0.0, []),
    ("prismatic_warding_sphere", "Prismatic Warding Sphere", "Esfera de Contencion Prismatica", "Shields against burning embers and weakening curses.", "Escudo prismatico inmune a quemaduras y debilitamiento.", "OFF_HAND", 3, "mage", 45, 8, 8, 0, 0.0, "FOCUS", None, 0.0, ["burn", "weaken"]),

    # --- HEAD Tier 3 ---
    # Universal
    ("crown_of_forgotten_king", "Crown of the Forgotten King", "Corona del Rey Olvidado", "Ancient gilded circlet exuding undeniable regality.", "Corona de oro antiguo que irradia autoridad y mando.", "HEAD", 3, None, 40, 4, 8, 0, 0.0, None, None, 0.0, []),
    ("paranoids_golden_coif", "Paranoid's Golden Coif", "Cofia Dorada del Desconfiado", "Lined with warding runes repelling unexpected deceit.", "Tejida con runas que evitan emboscadas y sorpresas.", "HEAD", 3, None, 25, 0, 6, 5, 0.12, None, None, 0.0, []),
    # Warrior
    ("warlords_dreadhelm", "Warlord's Dreadhelm", "Yelmo del Terror del Belicista", "Frightening iron mask instilling dread in onlookers.", "Mascara de hierro que aterra a las legiones enemigas.", "HEAD", 3, "warrior", 50, 4, 12, 0, 0.0, None, None, 0.0, []),
    ("immortal_visage", "Immortal Visage", "Semblante Inmortal", "Forged in titan embers, defying mortal frailty.", "Forjado en ascuas de titanes, burlando la fragilidad mortal.", "HEAD", 3, "warrior", 60, 0, 14, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("specter_cowl", "Specter Cowl", "Capucha del Espectro", "Woven from void strands, concealing the wearer's gaze.", "Hilada en hebras del vacio para ocultar toda mirada.", "HEAD", 3, "rogue", 30, 5, 0, 9, 0.15, None, None, 0.0, []),
    ("faceless_assassin_mask", "Faceless Assassin Mask", "Mascara del Asesino sin Rostro", "Erases personal presence to ensure fatal strikes.", "Borra la presencia personal para asegurar el golpe mortal.", "HEAD", 3, "rogue", 25, 6, 4, 8, 0.12, None, None, 0.0, []),
    # Mage
    ("archmage_diadem", "Arch-Mage Diadem", "Diadema del Archimago", "Priceless crown resonating with boundless arcane mastery.", "Corona incalculable que resuena con maestria arcana.", "HEAD", 3, "mage", 25, 14, 6, 0, 0.10, None, None, 0.0, []),
    ("crown_cosmic_insight", "Crown of Cosmic Insight", "Corona de Percepcion Cosmica", "Reveals hidden leylines across time and space.", "Revela corrientes místicas a traves del espacio-tiempo.", "HEAD", 3, "mage", 35, 16, 0, 4, 0.0, None, None, 0.0, []),

    # --- CHEST Tier 3 ---
    # Universal
    ("purifying_vestment_light", "Purifying Vestment of Light", "Vestidura Purificadora de Luz", "Woven with celestial silk granting status immunity.", "Seda celestial que disipa quemaduras, venenos y desgarros.", "CHEST", 3, None, 50, 0, 10, 0, 0.0, None, None, 0.0, ["burn", "poison", "bleed"]),
    ("spiked_dragon_carapace", "Spiked Dragon Carapace", "Caparazon de Dragon con Puas", "Ancient dragon scales forged into impenetrable plates.", "Escamas de dragon milenario forjadas en coraza indestructible.", "CHEST", 3, None, 60, 4, 12, 0, 0.0, None, None, 0.0, []),
    # Warrior
    ("cuirass_of_colossus", "Cuirass of the Colossus", "Coraza del Coloso", "Monumental armor carved from living mountains.", "Armadura monumental labrada en roca viva de cordillera.", "CHEST", 3, "warrior", 75, 0, 18, 0, 0.0, None, None, 0.0, []),
    ("bloodforged_plate", "Bloodforged Plate", "Placa Forjasangre", "Bathed in dragon's blood, fueling relentless warfare.", "Banada en sangre de dragon para alimentar matanzas eternas.", "CHEST", 3, "warrior", 55, 8, 14, 0, 0.05, None, None, 0.0, []),
    # Rogue
    ("nightstalker_master_vest", "Nightstalker Master Vest", "Chaleco Maestro del Acechador Nocturno", "Peak garment of guildmaster rogues.", "El atavio definitivo de los grandes maestros de gremio.", "CHEST", 3, "rogue", 40, 8, 8, 10, 0.12, None, None, 0.0, []),
    ("shadowdancer_raiment", "Shadowdancer Raiment", "Atavio del Danzarin Sombrio", "Fluid cloth flowing around blades like water.", "Ropaje fluido que esquiva filos como agua viva.", "CHEST", 3, "rogue", 35, 6, 6, 14, 0.15, None, None, 0.0, []),
    # Mage
    ("voidstrider_robes", "Voidstrider Robes", "Tunicas del Caminante del Vacio", "Shifting dark fabric feeding on pure arcane fallout.", "Tela cambiante que se nutre de resquicios del vacio.", "CHEST", 3, "mage", 45, 16, 7, 4, 0.08, None, None, 0.0, []),
    ("robes_astral_phoenix", "Robes of the Astral Phoenix", "Tunicas del Fenix Astral", "Radiant phoenix feathers igniting enemies upon contact.", "Plumas de fenix que envuelven en llamas a los agresores.", "CHEST", 3, "mage", 50, 14, 8, 0, 0.0, None, "burn", 0.40, []),

    # --- LEGS Tier 3 ---
    # Universal
    ("titan_tread_greaves", "Titan Tread Greaves", "Grebas de Pisada de Titan", "Massive legplates shaking the earth with each step.", "Laminas ciclopeas que estremecen el suelo a cada paso.", "LEGS", 3, None, 50, 0, 10, -2, 0.0, None, None, 0.0, []),
    ("boots_of_windstrider", "Boots of the Windstrider", "Botas del Vientoceleste", "Enchanted with bound Zephyrs for incredible speed.", "Imbuidas de cefiros para alcanzar velocidades imposibles.", "LEGS", 3, None, 35, 0, 6, 8, 0.08, None, None, 0.0, []),
    # Warrior
    ("juggernaut_legplates", "Juggernaut Legplates", "Placas de Pierna del Imparable", "Reinforced greaves ensuring no advance is stopped.", "Grebas reforzadas que impiden cualquier retroceso.", "LEGS", 3, "warrior", 60, 0, 14, 0, 0.0, None, None, 0.0, []),
    ("warlords_greaves", "Warlord's Greaves", "Grebas del Conquistador", "Spiked greaves used in brutal shield-wall scuffles.", "Grebas dentadas que arrollan en choques de escudos.", "LEGS", 3, "warrior", 45, 5, 11, 0, 0.0, None, None, 0.0, []),
    # Rogue
    ("ghostwalker_boots", "Ghostwalker Boots", "Botas del Caminafantasmas", "Allows the wearer to step beyond the boundary of sight.", "Permite deslizarse por los bordes mismos de la vision.", "LEGS", 3, "rogue", 25, 4, 0, 12, 0.12, None, None, 0.0, []),
    ("shadowrunner_breeches", "Shadowrunner Breeches", "Calzones del Corredor Sombrío", "Silent trousers facilitating supersonic sidesteps.", "Pantalones sigilosos que permiten esquivas supersónicas.", "LEGS", 3, "rogue", 30, 0, 5, 10, 0.10, None, None, 0.0, []),
    # Mage
    ("chronoweaver_trousers", "Chronoweaver Trousers", "Pantalones del Tejedor del Tiempo", "Manipulates personal time dilation around footsteps.", "Distorsiona la dilatacion temporal en torno a los pasos.", "LEGS", 3, "mage", 30, 12, 5, 6, 0.0, None, None, 0.0, []),
    ("celestial_silk_leggings", "Celestial Silk Leggings", "Calzas de Seda Celestial", "Spun from starlight, offering supernatural agility.", "Hiladas en luz estelar para conjurar con soltura astral.", "LEGS", 3, "mage", 40, 14, 6, 0, 0.06, None, None, 0.0, []),

    # --- SHOULDERS Tier 3 ---
    # Universal
    ("dragonscale_epaulets", "Dragon-Scale Epaulets", "Charreteras de Escama de Dragon", "Molten dragon plates absorbing direct concussions.", "Planchas igneas de dragon que desvian conmociones.", "SHOULDERS", 3, None, 40, 0, 9, 0, 0.0, None, None, 0.0, []),
    ("mantle_of_the_nomad", "Mantle of the Nomad", "Manto del Nomada Legendario", "Feathered mantle tested in thousands of battles.", "Manto de plumas probado en incontables batallas.", "SHOULDERS", 3, None, 30, 0, 5, 6, 0.06, None, None, 0.0, []),
    # Warrior
    ("fortress_pauldrons", "Fortress Pauldrons", "Hombreras Fortaleza", "Bastion-like spaulders protecting against overhead executions.", "Piezas que protegen los hombros de ejecuciones verticales.", "SHOULDERS", 3, "warrior", 50, 0, 12, 0, 0.0, None, None, 0.0, []),
    ("warmasters_spiked_shoulders", "Warmaster's Spiked Shoulders", "Espaldares Dentados de Belicista", "Fearsome spiked armor punishing enemy melee.", "Armadura con cuernos que hiere al menor forcejeo.", "SHOULDERS", 3, "warrior", 35, 6, 9, 0, 0.06, None, None, 0.0, []),
    # Rogue
    ("mantle_ghost_phantom", "Mantle of the Ghost Phantom", "Manto del Espectro Fantasmal", "Ethereal mantle blurring body contours into mist.", "Manto etereo que desdibuja el cuerpo en siluetas.", "SHOULDERS", 3, "rogue", 25, 6, 6, 10, 0.12, None, None, 0.0, []),
    ("shadowblade_pauldrons", "Shadowblade Pauldrons", "Hombreras de la Hoja Sombria", "Razor-sharp shoulder blades assisting in lethal maneuvers.", "Laminas afiladas en hombros para giros mortiferos.", "SHOULDERS", 3, "rogue", 20, 7, 4, 8, 0.14, None, None, 0.0, []),
    # Mage
    ("aetherflame_mantle", "Aetherflame Mantle", "Manto de Fuego Etereo", "Drapes the spellcaster in crackling arcane fires.", "Envuelve al conjurador en fuego arcano danzante.", "SHOULDERS", 3, "mage", 25, 14, 6, 0, 0.0, None, None, 0.0, []),
    ("void_touched_epaulets", "Void-Touched Epaulets", "Charreteras Tocadas por el Vacio", "Gathers void residues to empower deadly spells.", "Concentran residuos del vacio para hechizos letales.", "SHOULDERS", 3, "mage", 20, 15, 0, 5, 0.10, None, None, 0.0, []),

    # --- HANDS Tier 3 ---
    # Universal
    ("titans_iron_gauntlets", "Titan's Iron Gauntlets", "Guanteletes de Hierro del Titan", "Unforgiving iron fists multiplying crush impacts.", "Punetes de hierro macizo que multiplican el impacto.", "HANDS", 3, None, 40, 3, 8, 0, 0.0, None, None, 0.0, []),
    ("grip_of_the_executioner", "Grip of the Executioner", "Manoplas del Decapitador", "Forged to sever vital arteries without falter.", "Forjadas para segar miembros y arterias sin titubeo.", "HANDS", 3, None, 20, 6, 5, 5, 0.10, None, None, 0.0, []),
    # Warrior
    ("colossus_fists", "Colossus Fists", "Punetes del Coloso", "Massive gauntlets encasing wrists in mountain stone.", "Guanteletes que envuelven las manos en roca de montana.", "HANDS", 3, "warrior", 45, 4, 10, 0, 0.0, None, None, 0.0, []),
    ("gauntlets_of_ruin", "Gauntlets of Ruin", "Guanteletes de la Ruina", "Dark spiked gauntlets breaking armors on contact.", "Guanteletes con garras que astillan escudos.", "HANDS", 3, "warrior", 30, 8, 7, 0, 0.08, None, None, 0.0, []),
    # Rogue
    ("assassins_twin_grips", "Assassin's Twin-Grips", "Guantes de Garra de Asesino", "Provides supreme tactile control for dual daggers.", "Proporcionan tacto absoluto para empunaduras dobles.", "HANDS", 3, "rogue", 0, 7, 0, 8, 0.15, None, None, 0.0, []),
    ("master_poisoner_gloves", "Master Poisoner Gloves", "Guantes de Maestro Envenenador", "Permeated with venom, poisoning foes upon contact.", "Impregnados de toxinas para envenenar con cada tajo.", "HANDS", 3, "rogue", 25, 6, 4, 8, 0.0, None, "poison", 0.20, []),
    # Mage
    ("archmages_spellgloves", "Archmage's Spell-Gloves", "Guantes de Conjuro del Archimago", "Silk weaves dancing with lightning at the fingertips.", "Hilos de seda que descargan chispas en las yemas.", "HANDS", 3, "mage", 0, 14, 0, 6, 0.10, None, None, 0.0, []),
    ("hands_of_the_voidcaller", "Hands of the Voidcaller", "Manos del Conjurador del Vacio", "Dark gloves reaching into extraplanar dimensions.", "Guantes sombrios que abren grietas extraplanares.", "HANDS", 3, "mage", 30, 15, 5, 0, 0.0, None, None, 0.0, []),

    # --- WAIST Tier 3 ---
    # Universal
    ("girdle_of_earth_titan", "Girdle of the Earth Titan", "Faja del Titan de la Tierra", "Heavy stone-studded belt grounding the adventurer.", "Cinturon con rocas engarzadas que anclan al campeon.", "WAIST", 3, None, 45, 0, 10, 0, 0.0, None, None, 0.0, []),
    ("champions_belt", "Champion's Championship Belt", "Cinturon del Gran Campeon", "Ornate golden belt rewarding proven arena legends.", "Cinturon de oro cincelado que recompensa a campeones.", "WAIST", 3, None, 30, 4, 6, 4, 0.06, None, None, 0.0, []),
    # Warrior
    ("warlords_greatbelt", "Warlord's Greatbelt", "Gran Cinto del Belicista", "Banded steel girdle holding war trophy plates.", "Faja de laminas de acero con trofeos de batalla.", "WAIST", 3, "warrior", 50, 3, 11, 0, 0.0, None, None, 0.0, []),
    ("bloodforged_cincture", "Blood-Forged Cincture", "Cincho Forjasangre", "Runic girdle channeling martial wrath into raw vigor.", "Faja runica que transforma furia guerrera en vigor.", "WAIST", 3, "warrior", 35, 6, 8, 0, 0.06, None, None, 0.0, []),
    # Rogue
    ("master_rogues_sash", "Master Rogue's Sash", "Faja de Maestro Picaro", "Weighted sash housing throwing caltrops and daggers.", "Faja lastrada con compartimentos secretos y dardos.", "WAIST", 3, "rogue", 25, 5, 4, 8, 0.12, None, None, 0.0, []),
    ("shadowweaver_cord", "Shadow-Weaver Cord", "Cordon del Tejedor Sombrío", "Silent belt harmonizing agility and lethal instinct.", "Cinto sigiloso que acompasa agilidad e instinto mortal.", "WAIST", 3, "rogue", 20, 4, 0, 10, 0.14, None, None, 0.0, []),
    # Mage
    ("sash_of_the_archmage", "Sash of the Archmage", "Faja del Archimago", "Golden sash radiating concentrated mystical authority.", "Faja dorada que irradia autoridad mistica concentrada.", "WAIST", 3, "mage", 30, 14, 5, 0, 0.0, None, None, 0.0, []),
    ("cosmic_leyline_belt", "Cosmic Leyline Belt", "Cinturon de Lineas Ley Cosmicas", "Channels ambient cosmic leylines to quicken spellcraft.", "Canaliza lineas cosmicas para acelerar la hechiceria.", "WAIST", 3, "mage", 0, 16, 0, 5, 0.10, None, None, 0.0, []),
]

print(f"Total items defined: {len(ITEMS_DATA)}")
assert len(ITEMS_DATA) == 192, f"Expected 192, got {len(ITEMS_DATA)}"

# Check for unique IDs
ids = [x[0] for x in ITEMS_DATA]
assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"
print("All 192 items have unique IDs!")
