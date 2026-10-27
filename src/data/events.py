import copy
import random
from dataclasses import dataclass, field
from typing import Callable

from src.core import GameState
from src.core.i18n import i18n
from src.data.items import ITEM_CATALOG
from src.systems.status import create_bleed, create_poison, create_weaken, create_burn

if False:  # TYPE_CHECKING
    pass


@dataclass
class EventChoice:
    label_en: str
    label_es: str
    action_hook: Callable[['GameState'], str]
    is_available: Callable[['GameState'], bool] = field(default_factory=lambda: lambda state: True)

    @property
    def label(self) -> str:
        return self.label_es if i18n.locale == "es" else self.label_en


@dataclass
class GameEvent:
    id: str
    title_en: str
    title_es: str
    description_en: str
    description_es: str
    scene_type: str
    choices: list[EventChoice]
    resolved_text: str = ""

    @property
    def title(self) -> str:
        return self.title_es if i18n.locale == "es" else self.title_en

    @property
    def description(self) -> str:
        return self.description_es if i18n.locale == "es" else self.description_en


# Universal Events
UNIVERSAL_EVENTS = [
    GameEvent(
        id="wandering_scholar",
        title_en="The Wandering Scholar",
        title_es="El Erudito Errante",
        description_en="An old man in tattered robes sits by a small campfire. 'Knowledge has a price, traveler,' he wheezes. 'What would you learn?'",
        description_es="Un anciano con túnica andrajosa se sienta junto a una fogata. 'El conocimiento tiene un precio, viajero,' murmura. '¿Qué aprenderías?'",
        scene_type="DEFAULT",
        choices=[
            EventChoice(
                label_en="[30G] Study Martial Tactics (+2 ATK)",
                label_es="[30G] Estudiar Tácticas (+2 ATK)",
                is_available=lambda state: state.player.gold >= 30,
                action_hook=lambda state: (
                    setattr(state.player, 'gold', state.player.gold - 30),
                    setattr(state.player.base_stats, 'attack', state.player.base_stats.attack + 2),
                    "You train under the scholar. Your strikes grow more precise." if i18n.locale == "en" else "Entrenas con el erudito. Tus golpes se vuelven más precisos."
                )[-1]
            ),
            EventChoice(
                label_en="[30G] Study Evasive Footwork (+2 SPD)",
                label_es="[30G] Estudiar Evasión (+2 SPD)",
                is_available=lambda state: state.player.gold >= 30,
                action_hook=lambda state: (
                    setattr(state.player, 'gold', state.player.gold - 30),
                    setattr(state.player.base_stats, 'speed', state.player.base_stats.speed + 2),
                    "You practice footwork drills. Your agility improves." if i18n.locale == "en" else "Practicas ejercicios de piernas. Tu agilidad mejora."
                )[-1]
            ),
            EventChoice(
                label_en="Decline and move on",
                label_es="Declinar y avanzar",
                action_hook=lambda
                    state: "You nod respectfully and continue on your way." if i18n.locale == "en" else "Asientes con respeto y continúas tu camino."
            )
        ]
    ),
    GameEvent(
        id="desecrated_reliquary",
        title_en="Desecrated Reliquary",
        title_es="Relicario Profanado",
        description_en="A massive sarcophagus wrapped in rusted iron chains sits in the center of the room. It pulses with dark energy.",
        description_es="Un enorme sarcófago envuelto en cadenas oxidadas descansa en el centro de la sala. Pulsa con energía oscura.",
        scene_type="SHRINE",
        choices=[
            EventChoice(
                label_en="Pry it open (-20% HP, Greater Elixir)",
                label_es="Abrirlo por la fuerza (-20% HP, Elixir Mayor)",
                action_hook=lambda state: (
                    state.player.take_damage(int(state.player.max_hp * 0.2)),
                    state.player.inventory.add_to_pouch(ITEM_CATALOG["elixir_strength_greater"]),  # Example
                    "Dark energy lashes out as you open it, but you find a powerful elixir inside." if i18n.locale == "en" else "La energía oscura te azota al abrirlo, pero encuentras un poderoso elixir dentro."
                )[-1]
            ),
            EventChoice(
                label_en="Consecrate it (Heal 25 HP, +20 EXP)",
                label_es="Consagrarlo (Cura 25 HP, +20 EXP)",
                action_hook=lambda state: (
                    state.player.heal(25),
                    state.player.gain_experience(20),
                    "You say a prayer over the reliquary. The dark energy dissipates." if i18n.locale == "en" else "Dices una oración sobre el relicario. La energía oscura se disipa."
                )[-1]
            )
        ]
    )
]

# Biome Specific Events
BIOME_EVENTS = {
    "arboretum": [
        GameEvent(
            id="bramble_corpse",
            title_en="Bramble-Tangled Corpse",
            title_es="Cadáver Enredado en Zarzas",
            description_en="A long-dead adventurer is ensnared in thick, thorny vines. Something glints in their pouch.",
            description_es="Un aventurero muerto hace mucho está atrapado en gruesas enredaderas espinosas. Algo brilla en su bolsa.",
            scene_type="CORPSE",
            choices=[
                EventChoice(
                    label_en="Carefully cut vines (Chance for Gold/Potion or Bleed)",
                    label_es="Cortar zarzas (Probabilidad de Oro/Poción o Sangrado)",
                    action_hook=lambda state: (
                        (
                            setattr(state.player, 'gold', state.player.gold + 35),
                            state.player.inventory.add_to_pouch(ITEM_CATALOG["health_potion"]),
                            "You manage to retrieve the items unharmed." if i18n.locale == "en" else "Logras recuperar los objetos sin sufrir daño."
                        )[-1] if random.random() < 0.7 else (
                            setattr(state.player, 'gold', state.player.gold + 15),
                            state.player.apply_status(create_bleed(potency=2, duration=3)),
                            "The thorns slice your hands as you reach in, drawing blood." if i18n.locale == "en" else "Las espinas cortan tus manos al alcanzarlo, haciéndote sangrar."
                        )[-1]
                    )
                ),
                EventChoice(
                    label_en="Leave undisturbed",
                    label_es="No perturbar",
                    action_hook=lambda
                        state: "You decide the risk isn't worth it." if i18n.locale == "en" else "Decides que el riesgo no vale la pena."
                )
            ]
        ),
        GameEvent(
            id="fluorescent_mandragora",
            title_en="Fluorescent Mandragora Patch",
            title_es="Parche de Mandrágora Fluorescente",
            description_en="A patch of glowing mandragoras emits a strange, sweet aroma. Their bulbs thrum with vitality.",
            description_es="Un parche de mandrágoras brillantes emite un aroma extraño y dulce. Sus bulbos vibran de vitalidad.",
            scene_type="SHRINE",
            choices=[
                EventChoice(
                    label_en="Eat raw bulb (+20 Max HP, Poison)",
                    label_es="Comer bulbo crudo (+20 Max HP, Veneno)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'max_hp', state.player.base_stats.max_hp + 20),
                        setattr(state.player, 'current_hp', state.player.current_hp + 20),
                        state.player.apply_status(create_poison(potency=3, duration=3)),
                        "You choke down the bitter root. Your vitality surges, but nausea overtakes you." if i18n.locale == "en" else "Tragas la raíz amarga. Tu vitalidad aumenta, pero te invade la náusea."
                    )[-1]
                ),
                EventChoice(
                    label_en="Harvest sap (Major Health Flask)",
                    label_es="Cosechar savia (Frasco de Salud Mayor)",
                    action_hook=lambda state: (
                        state.player.inventory.add_to_pouch(ITEM_CATALOG["major_health_flask"]),
                        "You carefully extract the medicinal sap." if i18n.locale == "en" else "Extraes cuidadosamente la savia medicinal."
                    )[-1]
                )
            ]
        )
    ],
    "cathedral": [
        GameEvent(
            id="weeping_gargoyle",
            title_en="Weeping Gargoyle Font",
            title_es="Fuente de Gárgola Llorona",
            description_en="A stone gargoyle weeps crystal-clear water into a basin. The liquid shimmers with holy light.",
            description_es="Una gárgola de piedra llora agua cristalina en una vasija. El líquido brilla con luz sagrada.",
            scene_type="ALTAR",
            choices=[
                EventChoice(
                    label_en="Drink holy water (Cleanse, Heal 35% HP)",
                    label_es="Beber agua bendita (Limpiar, Cura 35% HP)",
                    action_hook=lambda state: (
                        state.player.cleanse_debuffs(),
                        state.player.heal(int(state.player.max_hp * 0.35)),
                        "The holy water purifies your body and mends your wounds." if i18n.locale == "en" else "El agua bendita purifica tu cuerpo y sana tus heridas."
                    )[-1]
                ),
                EventChoice(
                    label_en="Offer tithe (-25G, +5% Crit permanently)",
                    label_es="Ofrecer diezmo (-25G, +5% Crítico permanente)",
                    is_available=lambda state: state.player.gold >= 25,
                    action_hook=lambda state: (
                        setattr(state.player, 'gold', state.player.gold - 25),
                        setattr(state.player.base_stats, 'crit_chance', state.player.base_stats.crit_chance + 0.05),
                        "The gargoyle's eyes flash gold. Your strikes feel more lethal." if i18n.locale == "en" else "Los ojos de la gárgola brillan dorados. Tus golpes se sienten más letales."
                    )[-1]
                )
            ]
        ),
        GameEvent(
            id="chained_tome",
            title_en="Chained Heretic's Tome",
            title_es="Tomo de Hereje Encadenado",
            description_en="A heavy grimoire bound in chains lies on a pedestal. Whispers seem to emanate from its pages.",
            description_es="Un pesado grimorio encadenado descansa en un pedestal. Susurros parecen emanar de sus páginas.",
            scene_type="CHEST",
            choices=[
                EventChoice(
                    label_en="Read forbidden script (-15 HP, Gain Ability Choice)",
                    label_es="Leer escritura prohibida (-15 HP, Elegir Habilidad)",
                    action_hook=lambda state: (
                        state.player.take_damage(15),
                        state.player.pending_ability_choices.append("STANDARD"),
                        "Forbidden knowledge burns into your mind." if i18n.locale == "en" else "El conocimiento prohibido quema tu mente."
                    )[-1]
                ),
                EventChoice(
                    label_en="Scavenge gold inlays (+50G)",
                    label_es="Robar incrustaciones de oro (+50G)",
                    action_hook=lambda state: (
                        setattr(state.player, 'gold', state.player.gold + 50),
                        "You pry the precious metals from the cover, ignoring the whispers." if i18n.locale == "en" else "Arrancas los metales preciosos de la cubierta, ignorando los susurros."
                    )[-1]
                )
            ]
        )
    ],
    "ossuary": [
        GameEvent(
            id="brine_leech_basin",
            title_en="Brine Leech Basin",
            title_es="Cuenca de Sanguijuelas de Salmuera",
            description_en="A shallow pool filled with pale leeches swimming in salty water.",
            description_es="Un charco poco profundo lleno de sanguijuelas pálidas nadando en agua salada.",
            scene_type="ALTAR",
            choices=[
                EventChoice(
                    label_en="Endure leech therapy (-15 HP, +3 DEF permanently)",
                    label_es="Soportar terapia de sanguijuelas (-15 HP, +3 DEF permanente)",
                    action_hook=lambda state: (
                        state.player.take_damage(15),
                        setattr(state.player.base_stats, 'defense', state.player.base_stats.defense + 3),
                        "The leeches drain your blood, but your skin hardens like leather." if i18n.locale == "en" else "Las sanguijuelas drenan tu sangre, pero tu piel se endurece como el cuero."
                    )[-1]
                ),
                EventChoice(
                    label_en="Scrape salts (Obtain Cleansing Flask)",
                    label_es="Raspar sales (Obtener Frasco Purificador)",
                    action_hook=lambda state: (
                        state.player.inventory.add_to_pouch(ITEM_CATALOG["cleansing_flask"]),
                        "You carefully scrape the mineral salts from the edge of the basin." if i18n.locale == "en" else "Raspas cuidadosamente las sales minerales del borde de la cuenca."
                    )[-1]
                )
            ]
        ),
        GameEvent(
            id="sunken_relic",
            title_en="Sunken Relic Cache",
            title_es="Caché de Reliquias Hundidas",
            description_en="A stone chest rests at the bottom of a dark, murky pool.",
            description_es="Un cofre de piedra descansa en el fondo de un charco oscuro y turbio.",
            scene_type="CHEST",
            choices=[
                EventChoice(
                    label_en="Dive deep (45G, Elixir, 40% Weaken)",
                    label_es="Bucear profundo (45G, Elixir, 40% Debilitar)",
                    action_hook=lambda state: (
                        (
                            setattr(state.player, 'gold', state.player.gold + 45),
                            state.player.inventory.add_to_pouch(ITEM_CATALOG["elixir_celerity_greater"]),
                            state.player.apply_status(create_weaken(potency=2, duration=3)),
                            "You retrieve the treasure, but the freezing water drains your strength." if i18n.locale == "en" else "Recuperas el tesoro, pero el agua helada drena tu fuerza."
                        )[-1] if random.random() < 0.4 else (
                            setattr(state.player, 'gold', state.player.gold + 45),
                            state.player.inventory.add_to_pouch(ITEM_CATALOG["elixir_celerity_greater"]),
                            "You retrieve the treasure and emerge unharmed." if i18n.locale == "en" else "Recuperas el tesoro y emerges ileso."
                        )[-1]
                    )
                ),
                EventChoice(
                    label_en="Skim the shallows (+15G)",
                    label_es="Explorar la orilla (+15G)",
                    action_hook=lambda state: (
                        setattr(state.player, 'gold', state.player.gold + 15),
                        "You safely collect some loose coins near the surface." if i18n.locale == "en" else "Recoges monedas sueltas cerca de la superficie con seguridad."
                    )[-1]
                )
            ]
        )
    ],
    "foundry": [
        GameEvent(
            id="abandoned_soul_forge",
            title_en="Abandoned Soul-Forge",
            title_es="Forja de Almas Abandonada",
            description_en="A spectral fire still burns in this ancient forge. The anvil hums with residual power.",
            description_es="Un fuego espectral aún arde en esta antigua forja. El yunque zumba con poder residual.",
            scene_type="FORGE",
            choices=[
                EventChoice(
                    label_en="Temper weapon (+3 ATK permanently)",
                    label_es="Templar arma (+3 ATK permanente)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'attack', state.player.base_stats.attack + 3),
                        "You bathe your weapon in the spectral flames. Its edge grows sharper." if i18n.locale == "en" else "Bañas tu arma en las llamas espectrales. Su filo se vuelve más agudo."
                    )[-1]
                ),
                EventChoice(
                    label_en="Reinforce armor (+4 DEF, -1 SPD permanently)",
                    label_es="Reforzar armadura (+4 DEF, -1 SPD permanente)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'defense', state.player.base_stats.defense + 4),
                        setattr(state.player.base_stats, 'speed', max(1, state.player.base_stats.speed - 1)),
                        "You fuse ethereal steel to your armor. It is sturdier, but heavier." if i18n.locale == "en" else "Fusionas acero etéreo a tu armadura. Es más resistente, pero más pesada."
                    )[-1]
                )
            ]
        ),
        GameEvent(
            id="overheating_steam_vent",
            title_en="Overheating Steam Vent",
            title_es="Respiradero de Vapor Sobrecalentado",
            description_en="A high-pressure pipe is about to burst, venting scalding, alchemically-infused steam.",
            description_es="Una tubería de alta presión está a punto de estallar, ventilando vapor escaldador con infusión alquímica.",
            scene_type="FORGE",
            choices=[
                EventChoice(
                    label_en="Force valve (Greater Celerity Elixir, Burn)",
                    label_es="Forzar válvula (Elixir Celeridad Mayor, Quemadura)",
                    action_hook=lambda state: (
                        state.player.inventory.add_to_pouch(ITEM_CATALOG["elixir_celerity_greater"]),
                        state.player.apply_status(create_burn(potency=4, duration=3)),
                        "You wrestle the valve closed, securing the concentrated elixir, but the steam scalds you." if i18n.locale == "en" else "Cierras la válvula, asegurando el elixir concentrado, pero el vapor te quema."
                    )[-1]
                ),
                EventChoice(
                    label_en="Siphon steam (Elixir of Haste)",
                    label_es="Sifonear vapor (Elixir de Prisa)",
                    action_hook=lambda state: (
                        state.player.inventory.add_to_pouch(ITEM_CATALOG["elixir_of_haste"]),
                        "You carefully condense the escaping vapors into a potent draft." if i18n.locale == "en" else "Condensas cuidadosamente los vapores que escapan en un brebaje potente."
                    )[-1]
                )
            ]
        )
    ],
    "observatory": [
        GameEvent(
            id="cosmic_mirror_rift",
            title_en="Cosmic Mirror Rift",
            title_es="Grieta de Espejo Cósmico",
            description_en="A tear in reality reveals a swirling void of stars. It calls to your soul.",
            description_es="Un desgarro en la realidad revela un vacío arremolinado de estrellas. Llama a tu alma.",
            scene_type="PORTAL",
            choices=[
                EventChoice(
                    label_en="Gaze into rift (Gain EPIC Ability Choice)",
                    label_es="Mirar la grieta (Elegir Habilidad ÉPICA)",
                    action_hook=lambda state: (
                        state.player.pending_ability_choices.append("EPIC"),
                        "Visions of other worlds grant you profound insight." if i18n.locale == "en" else "Visiones de otros mundos te otorgan una visión profunda."
                    )[-1]
                ),
                EventChoice(
                    label_en="Shatter prism (-12 HP, +85G)",
                    label_es="Destrozar prisma (-12 HP, +85G)",
                    action_hook=lambda state: (
                        state.player.take_damage(12),
                        setattr(state.player, 'gold', state.player.gold + 85),
                        "You smash the stabilizing prism. The rift closes, leaving behind cosmic geodes." if i18n.locale == "en" else "Destrozas el prisma estabilizador. La grieta se cierra, dejando geodas cósmicas."
                    )[-1]
                )
            ]
        ),
        GameEvent(
            id="fallen_comet_shard",
            title_en="Fallen Comet Shard",
            title_es="Fragmento de Cometa Caído",
            description_en="A glowing meteorite rests in a crater, radiating intense celestial heat.",
            description_es="Un meteorito brillante descansa en un cráter, irradiando intenso calor celestial.",
            scene_type="SHRINE",
            choices=[
                EventChoice(
                    label_en="Channel starlight flame (+4 ATK, +5% Crit permanently)",
                    label_es="Canalizar llama estelar (+4 ATK, +5% Crítico permanente)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'attack', state.player.base_stats.attack + 4),
                        setattr(state.player.base_stats, 'crit_chance', state.player.base_stats.crit_chance + 0.05),
                        "You absorb the stellar fire. Your strikes burn with cosmic power." if i18n.locale == "en" else "Absorbes el fuego estelar. Tus golpes arden con poder cósmico."
                    )[-1]
                ),
                EventChoice(
                    label_en="Form stardust barrier (+30 Max HP, +3 DEF permanently)",
                    label_es="Formar barrera de polvo estelar (+30 Max HP, +3 DEF permanente)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'max_hp', state.player.base_stats.max_hp + 30),
                        setattr(state.player, 'current_hp', state.player.current_hp + 30),
                        setattr(state.player.base_stats, 'defense', state.player.base_stats.defense + 3),
                        "The stardust hardens around you, fortifying your life force." if i18n.locale == "en" else "El polvo estelar se endurece a tu alrededor, fortificando tu fuerza vital."
                    )[-1]
                )
            ]
        )
    ],
    "sanctum": [
        GameEvent(
            id="vampiric_blood_chalice",
            title_en="Vampiric Blood Chalice",
            title_es="Cáliz de Sangre Vampírica",
            description_en="An ornate golden chalice filled with crimson blood sits atop a dark altar.",
            description_es="Un ornamentado cáliz dorado lleno de sangre carmesí descansa sobre un oscuro altar.",
            scene_type="ALTAR",
            choices=[
                EventChoice(
                    label_en="Partake in communion (-20 HP, +6 ATK, +3 SPD, +8% Crit)",
                    label_es="Participar en comunión (-20 HP, +6 ATK, +3 SPD, +8% Crítico)",
                    action_hook=lambda state: (
                        state.player.take_damage(20),
                        setattr(state.player.base_stats, 'attack', state.player.base_stats.attack + 6),
                        setattr(state.player.base_stats, 'speed', state.player.base_stats.speed + 3),
                        setattr(state.player.base_stats, 'crit_chance', state.player.base_stats.crit_chance + 0.08),
                        "You drink the foul blood. It burns your veins but grants unholy strength." if i18n.locale == "en" else "Bebes la sangre fétida. Quema tus venas pero te otorga una fuerza impía."
                    )[-1]
                ),
                EventChoice(
                    label_en="Overturn altar (Heal 30 HP, +5 DEF permanently)",
                    label_es="Volcar altar (Cura 30 HP, +5 DEF permanente)",
                    action_hook=lambda state: (
                        state.player.heal(30),
                        setattr(state.player.base_stats, 'defense', state.player.base_stats.defense + 5),
                        "You desecrate the dark shrine. A wave of purifying light washes over you." if i18n.locale == "en" else "Profanas el oscuro santuario. Una ola de luz purificadora te baña."
                    )[-1]
                )
            ]
        ),
        GameEvent(
            id="duelist_weapon_rack",
            title_en="Duelist's Weapon Rack",
            title_es="Armero del Duelista",
            description_en="An elegant rack holding various masterwork weapons. One dagger in particular catches your eye.",
            description_es="Un elegante estante que sostiene varias armas maestras. Una daga en particular llama tu atención.",
            scene_type="CHEST",
            choices=[
                EventChoice(
                    label_en="Claim masterwork blade (Obtain Widowmaker Dirk)",
                    label_es="Reclamar hoja maestra (Obtener Daga Viuda Negra)",
                    action_hook=lambda state: (
                        state.player.inventory.add_to_pouch(ITEM_CATALOG["widowmaker_dirk"]),
                        "You carefully lift the deadly dagger from the rack." if i18n.locale == "en" else "Levantas cuidadosamente la daga mortal del estante."
                    )[-1]
                ),
                EventChoice(
                    label_en="Salvage grips (+3 SPD, +4% Crit, +50G)",
                    label_es="Robar empuñaduras (+3 SPD, +4% Crítico, +50G)",
                    action_hook=lambda state: (
                        setattr(state.player.base_stats, 'speed', state.player.base_stats.speed + 3),
                        setattr(state.player.base_stats, 'crit_chance', state.player.base_stats.crit_chance + 0.04),
                        setattr(state.player, 'gold', state.player.gold + 50),
                        "You dismantle the weapons for their exquisite materials and gold fittings." if i18n.locale == "en" else "Desmontas las armas por sus materiales exquisitos y accesorios de oro."
                    )[-1]
                )
            ]
        )
    ]
}


def get_random_event(biome_id: str, rng: random.Random | None = None) -> GameEvent:
    if rng is None:
        rng = random.Random()

    pool = UNIVERSAL_EVENTS + BIOME_EVENTS.get(biome_id, [])
    selected_event = rng.choice(pool)
    return copy.deepcopy(selected_event)
