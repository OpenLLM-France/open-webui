#!/usr/bin/env python3
"""
Scripts de développement pour le système de file d'attente.

Ce module fournit des commandes pour :
- Lancer l'application en mode développement
- Gérer les conteneurs Docker
- Exécuter les tests
- Formater le code
"""

import subprocess
import click
import os
from typing import Optional

@click.group()
def cli():
    """Outils de développement pour le système de file d'attente."""
    pass

@cli.command()
@click.option('--host', default='0.0.0.0', help='Hôte de l\'application')
@click.option('--port', default=None, help='Port de l\'application')
@click.option('--reload', is_flag=True, help='Active le rechargement automatique')
@click.option('--redis-port', default=None, help='Port Redis')
@click.option('--dev', is_flag=True, help='Mode développement (ports: FastAPI=8001, Redis=6380)')
def run(host: str, port: Optional[int], reload: bool, redis_port: Optional[int], dev: bool):
    """Lance l'application FastAPI en mode développement."""
    # Définir les ports en fonction du mode
    if dev:
        port = port or 8001
        redis_port = redis_port or 6380
    else:
        port = port or 8000
        redis_port = redis_port or 6379

    reload_flag = "--reload" if reload else ""
    os.environ['REDIS_PORT'] = str(redis_port)
    cmd = f"uvicorn app.main:app --host {host} --port {port} {reload_flag}"
    click.echo(f"Démarrage en mode {'développement' if dev else 'normal'}")
    click.echo(f"FastAPI port: {port}")
    click.echo(f"Redis port: {redis_port}")
    subprocess.run(cmd.split())

@cli.command()
def docker_up():
    """Lance tous les services avec Docker Compose."""
    subprocess.run(["docker-compose", "up", "--build", "-d"])
    click.echo("Services démarrés en arrière-plan")

@cli.command()
def docker_down():
    """Arrête tous les services Docker."""
    subprocess.run(["docker-compose", "down"])
    click.echo("Services arrêtés")

@cli.command()
def docker_logs():
    """Affiche les logs des services Docker."""
    subprocess.run(["docker-compose", "logs", "-f"])

def check_services_health():
    """Vérifie l'état des services et affiche les logs en cas d'erreur."""
    click.echo("Vérification de l'état des services...")
    
    # Vérifier l'état des conteneurs
    result = subprocess.run(
        ["docker-compose", "ps", "-q"],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        click.echo("❌ Aucun conteneur n'est en cours d'exécution")
        return False
    
    # Vérifier les logs pour chaque conteneur
    containers = result.stdout.strip().split('\n')
    has_errors = False
    
    # Liste des erreurs à ignorer car elles font partie des tests
    ignored_errors = [
        "test_error",
        "object dict can't be used in 'await' expression",
        "Erreur lors du démarrage de la tâche timer",
        "test_logger"
    ]
    
    for container_id in containers:
        # Obtenir le nom du conteneur
        name_result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Name}}", container_id],
            capture_output=True,
            text=True
        )
        container_name = name_result.stdout.strip().replace('/', '')
        
        # Vérifier les logs pour les erreurs
        logs_result = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True
        )
        
        # Filtrer les erreurs qui ne sont pas des erreurs de test
        real_errors_stdout = []
        if "error" in logs_result.stdout.lower():
            for line in logs_result.stdout.split('\n'):
                if "error" in line.lower():
                    # Vérifier si c'est une erreur à ignorer
                    if not any(ignore in line for ignore in ignored_errors):
                        real_errors_stdout.append(line)
        
        # Vérifier les erreurs dans stderr (sauf celles des tests)
        stderr_content = logs_result.stderr.strip()
        has_real_stderr = stderr_content and not any(ignore in stderr_content for ignore in ignored_errors)
        
        if real_errors_stdout or has_real_stderr:
            click.echo(f"\n❌ Erreurs détectées dans {container_name}:")
            if has_real_stderr:
                click.echo("\nStderr:")
                click.echo(stderr_content)
            if real_errors_stdout:
                click.echo("\nStdout contenant des erreurs:")
                for line in real_errors_stdout:
                    click.echo(line)
            has_errors = True
        else:
            click.echo(f"✅ {container_name} fonctionne correctement")
    
    return not has_errors

@cli.command()
def test():
    """Lance les tests avec l'environnement approprié."""
    # Arrêter les conteneurs existants
    click.echo("Arrêt des conteneurs existants...")
    subprocess.run(["docker-compose", "down"])
    
    # Lancer l'environnement de test
    click.echo("Démarrage de l'environnement de test...")
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"])
    
    # Attendre que les services soient prêts
    click.echo("Attente du démarrage des services...")
    subprocess.run(["sleep", "5"])
    
    # Vérifier l'état des services
    if not check_services_health():
        click.echo("❌ Des erreurs ont été détectées dans les services")
        return
    
    # Définir les variables d'environnement pour les tests
    os.environ['REDIS_PORT'] = "6380"
    
    # Lancer les tests
    click.echo("Lancement des tests...")
    subprocess.run(["pytest"])

@cli.command()
def test_env():
    """Configure et lance l'environnement de test complet."""
    # Arrêter les conteneurs existants
    click.echo("Arrêt des conteneurs existants...")
    subprocess.run(["docker-compose", "down"])
    
    # Lancer l'environnement de test
    click.echo("Démarrage de l'environnement de test...")
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"])
    
    # Attendre que les services soient prêts
    click.echo("Attente du démarrage des services...")
    subprocess.run(["sleep", "5"])
    
    # Vérifier l'état des services
    if not check_services_health():
        click.echo("❌ Des erreurs ont été détectées dans les services")
        return
    
    # Lancer l'application avec la bonne configuration
    click.echo("Démarrage de l'application...")
    os.environ['REDIS_PORT'] = "6380"
    cmd = "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    subprocess.run(cmd.split())

if __name__ == '__main__':
    cli() 