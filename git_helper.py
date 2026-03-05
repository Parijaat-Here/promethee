#!/usr/bin/env python3
"""
git_helper.py — Assistant Git interactif pour Prométhée
Usage : python git_helper.py
"""

import os
import subprocess
import sys


# ── Couleurs ANSI ─────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    GREY    = "\033[90m"

def ok(msg):    print(f"{C.GREEN}✔  {msg}{C.RESET}")
def err(msg):   print(f"{C.RED}✘  {msg}{C.RESET}")
def info(msg):  print(f"{C.CYAN}ℹ  {msg}{C.RESET}")
def warn(msg):  print(f"{C.YELLOW}⚠  {msg}{C.RESET}")
def title(msg): print(f"\n{C.BOLD}{C.BLUE}{'─' * 50}\n  {msg}\n{'─' * 50}{C.RESET}")
def sep():      print(f"{C.GREY}{'─' * 50}{C.RESET}")


# ── Exécution de commandes Git ────────────────────────────────────────────────

def run(cmd: list[str], capture: bool = False) -> tuple[int, str, str]:
    """Exécute une commande shell et retourne (code, stdout, stderr)."""
    env = os.environ.copy()
    # Désactiver l'outil graphique de mot de passe (KDE/ksshaskpass)
    env.pop("SSH_ASKPASS", None)
    env.pop("GIT_ASKPASS", None)
    env["GIT_TERMINAL_PROMPT"] = "1"

    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        env=env,
    )
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def git(*args, capture=False) -> tuple[int, str, str]:
    return run(["git"] + list(args), capture=capture)


# ── Vérifications préalables ──────────────────────────────────────────────────

def check_git_repo() -> bool:
    code, _, _ = git("rev-parse", "--git-dir", capture=True)
    return code == 0


def check_identity() -> bool:
    _, name, _  = git("config", "user.name",  capture=True)
    _, email, _ = git("config", "user.email", capture=True)
    if not name or not email:
        warn("Identité Git non configurée.")
        name  = input("  Ton nom  : ").strip()
        email = input("  Ton e-mail : ").strip()
        git("config", "--global", "user.name",  name)
        git("config", "--global", "user.email", email)
        ok(f"Identité enregistrée : {name} <{email}>")
    return True


def get_current_branch() -> str:
    _, branch, _ = git("branch", "--show-current", capture=True)
    return branch or "main"


def has_remote() -> bool:
    code, out, _ = git("remote", capture=True)
    return code == 0 and bool(out)


def has_commits() -> bool:
    code, _, _ = git("log", "--oneline", "-1", capture=True)
    return code == 0


# ── Actions ───────────────────────────────────────────────────────────────────

def action_status():
    title("STATUT DU DÉPÔT")

    if not check_git_repo():
        err("Ce dossier n'est pas un dépôt Git.")
        return

    # Branche et remote
    branch = get_current_branch()
    _, remote_url, _ = git("remote", "get-url", "origin", capture=True)
    info(f"Branche courante : {C.BOLD}{branch}{C.RESET}")
    if remote_url:
        info(f"Dépôt distant    : {remote_url}")
    else:
        warn("Aucun dépôt distant configuré.")

    sep()

    # Fichiers modifiés
    code, out, _ = git("status", "--short", capture=True)
    if out:
        print(f"\n{C.YELLOW}Fichiers modifiés :{C.RESET}")
        for line in out.splitlines():
            status = line[:2]
            fname  = line[3:]
            color  = C.RED if "D" in status else C.YELLOW if "M" in status else C.GREEN
            print(f"  {color}{status}{C.RESET}  {fname}")
    else:
        ok("Aucune modification en cours — dépôt propre.")

    sep()

    # Historique récent
    print(f"\n{C.CYAN}5 derniers commits :{C.RESET}")
    git("log", "--oneline", "--graph", "--decorate", "-5")


def action_commit_push():
    title("COMMIT & PUSH")

    if not check_git_repo():
        err("Ce dossier n'est pas un dépôt Git.")
        return

    check_identity()

    # Vérifier s'il y a des modifications
    _, short, _ = git("status", "--short", capture=True)
    if not short:
        warn("Aucune modification détectée. Rien à committer.")
        return

    # Afficher ce qui va être commité
    print(f"\n{C.YELLOW}Fichiers qui seront ajoutés :{C.RESET}")
    for line in short.splitlines():
        print(f"  {line}")

    print()
    message = input(f"{C.BOLD}Message du commit : {C.RESET}").strip()
    if not message:
        err("Message vide — commit annulé.")
        return

    # git add .
    code, _, stderr = git("add", ".")
    if code != 0:
        err(f"Erreur lors de git add : {stderr}")
        return
    ok("Fichiers ajoutés (git add .)")

    # git commit
    code, _, stderr = git("commit", "-m", message)
    if code != 0:
        err(f"Erreur lors du commit : {stderr}")
        return
    ok(f"Commit créé : « {message} »")

    # git push
    branch = get_current_branch()
    info(f"Push vers origin/{branch}…")
    code, _, stderr = git("push")
    if code != 0:
        err(f"Erreur lors du push :\n  {stderr}")
        warn("Si le token a expiré, génère-en un nouveau sur GitHub.")
    else:
        ok("Push réussi ✓")


def action_pull():
    title("PULL — Récupérer depuis GitHub")

    if not check_git_repo():
        err("Ce dossier n'est pas un dépôt Git.")
        return

    if not has_remote():
        err("Aucun dépôt distant configuré.")
        return

    branch = get_current_branch()
    info(f"Pull depuis origin/{branch}…")
    code, _, stderr = git("pull")
    if code != 0:
        err(f"Erreur lors du pull :\n  {stderr}")
        if "divergent" in stderr or "unrelated" in stderr:
            warn("Essaie : git pull --allow-unrelated-histories")
    else:
        ok("Pull réussi — dépôt à jour.")


def action_init_push():
    title("PREMIER PUSH — Initialisation")

    # Étape 1 : git init si nécessaire
    if check_git_repo():
        info("Dépôt Git déjà initialisé.")
    else:
        code, _, stderr = git("init")
        if code != 0:
            err(f"Erreur git init : {stderr}")
            return
        ok("Dépôt Git initialisé.")

    check_identity()

    # Étape 2 : URL du dépôt distant
    if has_remote():
        _, url, _ = git("remote", "get-url", "origin", capture=True)
        info(f"Remote déjà configuré : {url}")
        change = input("  Modifier l'URL ? (o/N) : ").strip().lower()
        if change == "o":
            url = input("  Nouvelle URL GitHub (https://github.com/...) : ").strip()
            git("remote", "set-url", "origin", url)
            ok(f"URL mise à jour : {url}")
    else:
        url = input("  URL du dépôt GitHub (https://github.com/...) : ").strip()
        if not url:
            err("URL vide — abandon.")
            return
        git("remote", "add", "origin", url)
        ok(f"Remote ajouté : {url}")

    # Étape 3 : Commit initial
    if has_commits():
        info("Des commits existent déjà.")
    else:
        _, short, _ = git("status", "--short", capture=True)
        if not short:
            warn("Aucun fichier à committer. Ajoute des fichiers d'abord.")
            return
        message = input("  Message du commit initial [Initial commit] : ").strip()
        if not message:
            message = "Initial commit"
        git("add", ".")
        code, _, stderr = git("commit", "-m", message)
        if code != 0:
            err(f"Erreur commit : {stderr}")
            return
        ok(f"Commit créé : « {message} »")

    # Étape 4 : Branche main
    git("branch", "-M", "main")
    ok("Branche renommée en 'main'.")

    # Étape 5 : Push
    info("Push initial vers origin/main…")
    code, _, stderr = git("push", "-u", "origin", "main")
    if code != 0:
        err(f"Erreur push : {stderr}")
        if "fetch first" in stderr or "rejected" in stderr:
            warn("Le dépôt GitHub contient déjà des fichiers.")
            choice = input("  Fusionner avec --allow-unrelated-histories ? (o/N) : ").strip().lower()
            if choice == "o":
                git("pull", "origin", "main", "--allow-unrelated-histories")
                code, _, stderr = git("push", "-u", "origin", "main")
                if code == 0:
                    ok("Push réussi après fusion ✓")
                else:
                    err(f"Échec : {stderr}")
    else:
        ok("Premier push réussi ✓")
        ok(f"Projet publié sur GitHub.")


def action_history():
    title("HISTORIQUE DES COMMITS")

    if not check_git_repo():
        err("Ce dossier n'est pas un dépôt Git.")
        return

    if not has_commits():
        warn("Aucun commit pour l'instant.")
        return

    nb = input("  Nombre de commits à afficher [10] : ").strip()
    nb = nb if nb.isdigit() else "10"

    git("log", "--oneline", "--graph", "--decorate", f"-{nb}")


# ── Menu principal ────────────────────────────────────────────────────────────

MENU = [
    ("Statut du dépôt",               action_status),
    ("Commit & Push  (mise à jour)",   action_commit_push),
    ("Pull           (récupérer)",     action_pull),
    ("Premier push   (initialisation)",action_init_push),
    ("Historique des commits",         action_history),
    ("Quitter",                        None),
]


def menu():
    # Aller dans le dossier du script (= racine du projet)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print(f"""
{C.BOLD}{C.GREEN}
  ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗███████╗███████╗
  ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║██╔════╝██╔════╝
  ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║█████╗  █████╗
  ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║██╔══╝  ██╔══╝
  ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║███████╗███████╗
  ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝
{C.RESET}{C.GREY}  Assistant Git interactif — Prométhée AI{C.RESET}
    """)

    info(f"Dossier de travail : {C.BOLD}{script_dir}{C.RESET}")

    while True:
        print(f"\n{C.BOLD}  Que veux-tu faire ?{C.RESET}\n")
        for i, (label, _) in enumerate(MENU, 1):
            icon = "🚪" if label == "Quitter" else f"{C.CYAN}{i}{C.RESET}"
            print(f"  [{icon}]  {label}")

        print()
        choice = input(f"{C.BOLD}  Choix (1-{len(MENU)}) : {C.RESET}").strip()

        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
            warn("Choix invalide.")
            continue

        idx = int(choice) - 1
        label, action = MENU[idx]

        if action is None:
            print(f"\n{C.GREEN}  Au revoir !{C.RESET}\n")
            sys.exit(0)

        try:
            action()
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}  Action annulée.{C.RESET}")

        input(f"\n{C.GREY}  [ Appuie sur Entrée pour revenir au menu ]{C.RESET}")


# ── Point d'entrée ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print(f"\n{C.GREEN}  Au revoir !{C.RESET}\n")
        sys.exit(0)
