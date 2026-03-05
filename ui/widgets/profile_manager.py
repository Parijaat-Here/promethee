# ============================================================================
# Prométhée — Assistant IA desktop
# ============================================================================
# Auteur  : Pierre COUGET
# Licence : GNU Affero General Public License v3.0 (AGPL-3.0)
#           https://www.gnu.org/licenses/agpl-3.0.html
# Année   : 2026
# ----------------------------------------------------------------------------
# Ce fichier fait partie du projet Prométhée.
# Vous pouvez le redistribuer et/ou le modifier selon les termes de la
# licence AGPL-3.0 publiée par la Free Software Foundation.
# ============================================================================

"""
profile_manager.py — Gestionnaire de profils/prompts système
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional


# ── Sérialisation YAML avec style bloc pour les prompts multilignes ────────
# Sans cette configuration, yaml.dump utilise des guillemets simples avec \n
# littéraux, ce qui rend le fichier illisible et difficile à éditer à la main.

class _BlockStr(str):
    """Marqueur pour forcer le style bloc YAML sur les chaînes multilignes."""

def _block_representer(dumper: yaml.Dumper, data: "_BlockStr") -> yaml.ScalarNode:
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

yaml.add_representer(_BlockStr, _block_representer)


def _to_block(obj):
    """Convertit récursivement toutes les str en _BlockStr."""
    if isinstance(obj, dict):
        return {k: _to_block(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_block(i) for i in obj]
    if isinstance(obj, str):
        return _BlockStr(obj)
    return obj


class ProfileManager:
    """Gestion des profils de prompts système."""

    def __init__(self, prompts_file: str = "prompts.yml"):
        self.prompts_file = Path(prompts_file)
        self.profiles: Dict[str, str] = {}
        self.profile_tools: Dict[str, Dict] = {}  # {profile: {enabled: [...], disabled: [...]}}
        self.profile_skills: Dict[str, List[str]] = {}  # {profile: [slug1, slug2, ...]}
        self.current_profile: str = "Aucun rôle"
        self._load_profiles()

    def _load_profiles(self):
        """Charge les profils depuis le fichier YAML."""
        try:
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

                if data and 'prompts' in data:
                    for name, config in data['prompts'].items():
                        prompt = config.get('prompt', '')
                        self.profiles[name] = prompt
                        # Familles d'outils associées au profil (optionnel)
                        tools_cfg = config.get('tools', {})
                        self.profile_tools[name] = {
                            'enabled':  list(tools_cfg.get('enabled',  [])),
                            'disabled': list(tools_cfg.get('disabled', [])),
                        }
                        # Skills épinglés pour ce profil
                        skills_cfg = config.get('skills', {})
                        self.profile_skills[name] = list(skills_cfg.get('pinned', []))

                # S'assurer qu'il y a au moins "Aucun rôle"
                if "Aucun rôle" not in self.profiles:
                    self.profiles["Aucun rôle"] = ""
                    self.profile_tools["Aucun rôle"] = {'enabled': [], 'disabled': []}
                    self.profile_skills["Aucun rôle"] = []

        except Exception as e:
            print(f"[ProfileManager] Erreur chargement profils : {e}")
            self.profiles = {"Aucun rôle": ""}
            self.profile_tools = {"Aucun rôle": {'enabled': [], 'disabled': []}}
            self.profile_skills = {"Aucun rôle": []}

    def get_profile_names(self) -> List[str]:
        """Retourne la liste des noms de profils."""
        return list(self.profiles.keys())

    def get_prompt(self, profile_name: str) -> str:
        """Retourne le prompt système d'un profil."""
        return self.profiles.get(profile_name, "")

    def get_current_prompt(self) -> str:
        """Retourne le prompt du profil actuel."""
        return self.get_prompt(self.current_profile)

    def set_current_profile(self, profile_name: str):
        """Définit le profil actuel."""
        if profile_name in self.profiles:
            self.current_profile = profile_name

    def add_profile(self, name: str, prompt: str):
        """Ajoute un nouveau profil."""
        self.profiles[name] = prompt
        self._save_profiles()

    def remove_profile(self, name: str):
        """Supprime un profil (sauf "Aucun rôle")."""
        if name != "Aucun rôle" and name in self.profiles:
            del self.profiles[name]
            if self.current_profile == name:
                self.current_profile = "Aucun rôle"
            self._save_profiles()

    def update_profile(self, name: str, prompt: str):
        """Met à jour le prompt d'un profil existant."""
        if name in self.profiles:
            self.profiles[name] = prompt
            self._save_profiles()

    def get_tool_families(self, profile_name: str) -> Dict:
        """Retourne les familles d'outils associées à un profil.

        Returns
        -------
        dict
            {'enabled': [...], 'disabled': [...]}
            Listes vides = pas de contrainte (tout activé par défaut).
        """
        return self.profile_tools.get(profile_name, {'enabled': [], 'disabled': []})

    def set_tool_families(self, profile_name: str, enabled: List[str], disabled: List[str]):
        """Définit les familles d'outils d'un profil et sauvegarde."""
        self.profile_tools[profile_name] = {'enabled': enabled, 'disabled': disabled}
        self._save_profiles()

    def get_pinned_skills(self, profile_name: str) -> List[str]:
        """Retourne la liste des slugs des skills épinglés pour un profil."""
        return list(self.profile_skills.get(profile_name, []))

    def set_pinned_skills(self, profile_name: str, slugs: List[str]) -> None:
        """Définit les skills épinglés d'un profil et sauvegarde."""
        self.profile_skills[profile_name] = list(slugs)
        self._save_profiles()

    def _save_profiles(self):
        """Sauvegarde les profils dans le fichier YAML."""
        prompts_data = {}
        for name, prompt in self.profiles.items():
            entry: Dict = {'prompt': prompt}
            tools_cfg = self.profile_tools.get(name, {'enabled': [], 'disabled': []})
            if tools_cfg['enabled'] or tools_cfg['disabled']:
                entry['tools'] = {}
                if tools_cfg['enabled']:
                    entry['tools']['enabled'] = tools_cfg['enabled']
                if tools_cfg['disabled']:
                    entry['tools']['disabled'] = tools_cfg['disabled']
            # Skills épinglés
            pinned = self.profile_skills.get(name, [])
            if pinned:
                entry['skills'] = {'pinned': pinned}
            prompts_data[name] = entry
        data = {'prompts': prompts_data}

        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                yaml.dump(_to_block(data), f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)
        except Exception as e:
            print(f"[ProfileManager] Erreur sauvegarde profils : {e}")

    def reload(self):
        """Recharge les profils depuis le fichier."""
        self.profiles = {}
        self.profile_tools = {}
        self.profile_skills = {}
        self._load_profiles()


# Instance globale
_profile_manager = ProfileManager()


def get_profile_manager() -> ProfileManager:
    """Retourne l'instance globale du gestionnaire de profils."""
    return _profile_manager
