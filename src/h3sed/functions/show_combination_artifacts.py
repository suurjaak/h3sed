from collections import defaultdict
import step
import h3sed


def show_combination_artifacts(savefile=None, heroes=(), **kwargs):
    """
    Returns text overview of complete and incomplete combination artifacts over player factions.

    Sample output:

    Faction: Red Player

    Assembled combination artifacts:
    - Admiral's Hat:
      - Adele equipment
      - Kyrre equipment
    - Golden Goose:
      - Xeron equipment

    Unassembled but combinable artifacts:
    - Golden Goose:
      - Endless Bag of Gold (Xeron inventory)
      - Endless Sack of Gold (Xeron inventory)
      - Endless Purse of Gold (Adele inventory)

    Lacking required parts:
    - Wizard's Well:
        Available:
        - Charm of Mana (Xeron equipment)
        - Charm of Mana (Xeron inventory)
        - Mystic Orb of Mana (Adele equipment)
        Missing:
        - Talisman of Mana
    """
    global defaultdict, step, h3sed, TEMPLATE # Mandatory, to work as a free function
    if savefile is None:
        return "No savefile open."

    version = savefile.version if savefile else None
    ASSEMBLED, SINGLE, EQ, INV = 0, 1, "equipment", "inventory"
    COMBINATION_ARTIFACTS = h3sed.metadata.Store.get("combination_artifacts", version=version)
    COMPONENT_TO_ASSEMBLED = {b: a for a, bb in COMBINATION_ARTIFACTS.items() for b in bb}

    # {faction: {assembled|single: artifact: {"equipment"|"inventory": [hero, ]}}}
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    # Collect information on all combination and component artifacts on heroes, by faction
    for hero in heroes:
        if "neutral" == h3sed.hero.Profile.make_faction_text(hero.profile.faction, version):
            continue # for hero
        for combo_artifact, components in COMBINATION_ARTIFACTS.items():
            for category, artifacts in zip((ASSEMBLED, SINGLE), ([combo_artifact], components)):
                for artifact in artifacts:
                    for property in (EQ, INV):
                        if artifact in hero.properties[property]:
                            data[hero.profile.faction][category][artifact][property].append(hero)

    outputs = []
    # Produce outputs per faction
    for faction in sorted(data, key=lambda x: h3sed.hero.Profile.make_faction_text(x, version)):

        # {combination artifact: {hero: ["equipment"|"inventory", ]}}
        assembled_artifacts = data[faction][ASSEMBLED]
        # {combination_artifact: [[(component artifact, hero, "equipment"|"inventory")], ]}
        available_artifacts = defaultdict(list)
        # {combination_artifact: [[(component artifact, hero, "equipment"|"inventory")], ]}
        incomplete_artifacts = defaultdict(list)
        # {combination_artifact: [component artifact, ]}
        missing_artifacts = defaultdict(list)

        # Collect information on uncombined but complete combination artifacts
        for component_artifact, owners in list(data[faction][SINGLE].items()):
            while owners: # Will become empty as iterations remove artifacts
                combo_artifact = COMPONENT_TO_ASSEMBLED[component_artifact]
                other_components = COMBINATION_ARTIFACTS[combo_artifact][:]
                other_components.remove(component_artifact)
                if not all(map(data[faction][SINGLE].get, other_components)): # Not all available
                    break # while owners

                prop = next(filter(owners.get, (EQ, INV)))
                hero = owners[prop].pop(0)            # NB: modifying data-variable
                if not owners[prop]: owners.pop(prop) # NB: modifying data-variable

                component_set = [(component_artifact, hero, prop)]
                while other_components:
                    component_artifact2 = other_components.pop(0)
                    owners2 = data[faction][SINGLE][component_artifact2]
                    # Prefer same hero, and same property
                    prop2 = prop if owners2.get(prop) and hero in owners2[prop] else None
                    if prop2 is None: prop2 = next((p for p, hh in owners2.items() if hero in hh), None)
                    if prop2 is None: prop2 = next(filter(owners2.get, (EQ, INV)))
                    hero2_index = owners2[prop2].index(hero) if hero in owners2[prop2] else 0
                    hero2 = owners2[prop2].pop(hero2_index)   # NB: modifying data-variable
                    if not owners2[prop2]: owners2.pop(prop2) # NB: modifying data-variable

                    component_set.append((component_artifact2, hero2, prop2))
                available_artifacts[combo_artifact].append(component_set)

        # Collect information on remaining incomplete combination artifacts
        for component_artifact, owners in list(data[faction][SINGLE].items()):
            if not owners: # Will become empty as iterations remove artifacts
                continue # for component_artifact
            combo_artifact = COMPONENT_TO_ASSEMBLED[component_artifact]
            existing_pieces = [] # [(component artifact, hero, property), ]
            missing_pieces = [] # [component artifact, ]
            for component_artifact2 in COMBINATION_ARTIFACTS[combo_artifact]:
                for prop, heroes2 in data[faction][SINGLE].get(component_artifact2, {}).items():
                    existing_pieces.extend((component_artifact2, h, prop) for h in heroes2)
                if not data[faction][SINGLE].get(component_artifact2):
                    missing_pieces.append(component_artifact2)
                else:
                    data[faction][SINGLE][component_artifact2].clear() # NB: modifying data-variable
            incomplete_artifacts[combo_artifact].extend(existing_pieces)
            missing_artifacts[combo_artifact].extend(missing_pieces)

        tpl_args = dict(
            faction=faction, version=version,
            assembled_artifacts=assembled_artifacts, available_artifacts=available_artifacts,
            incomplete_artifacts=incomplete_artifacts, missing_artifacts=missing_artifacts,
        )
        outputs.append(step.Template(TEMPLATE.strip(), strip=False).expand(**tpl_args))

    if not outputs:
        return "No combination artifacts or component parts in any faction."
    return ("\n%s\n" % ("-" * 40)).join(outputs)


TEMPLATE = """
<%
import h3sed
%>
Faction: {{ h3sed.hero.Profile.make_faction_text(faction, version) }}
%if assembled_artifacts:

Assembled combination artifacts:
    %for artifact, owners in sorted(assembled_artifacts.items()):
- {{ artifact }}:
<%
entries = [(hero, prop) for prop, heroes in owners.items() for hero in heroes]
%>
        %for hero, property in sorted(entries):
  - {{ hero.name }} {{ property }}
        %endfor
    %endfor
%endif
%if available_artifacts:

Unassembled but complete combination artifacts:
    %for combination_artifact, available_sets in sorted(available_artifacts.items()):
        %for component_set in available_sets:
- {{ combination_artifact }}:
            %for component_artifact, hero, property in sorted(component_set):
  - {{ component_artifact }} ({{ hero.name }} {{ property }})
            %endfor
        %endfor
    %endfor
%endif
%if incomplete_artifacts:

Incomplete combination artifacts:
    %for combination_artifact, existing_pieces in sorted(incomplete_artifacts.items()):
- {{ combination_artifact }}:
    Available:
        %for component_artifact, hero, property in sorted(existing_pieces):
    - {{ component_artifact }} ({{ hero.name }} {{ property }})
        %endfor
    Missing:
        %for component_artifact in sorted(missing_artifacts[combination_artifact]):
    - {{ component_artifact }}
        %endfor
    %endfor
%endif
    """
