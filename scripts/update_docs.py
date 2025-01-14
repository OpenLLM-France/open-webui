#!/usr/bin/env python3

import click
import subprocess
import os

@click.group()
def cli():
    """Commandes pour mettre à jour la documentation"""
    pass

@cli.command()
def readme():
    """Met à jour le README avec les résultats des tests"""
    test_output = subprocess.run(['poetry', 'run', 'pytest', '-v', '--no-header', '--tb=no'], capture_output=True, text=True)
    
    # Filtrer les lignes pour ne garder que les résultats des tests
    filtered_lines = []
    for line in test_output.stdout.split('\n'):
        if line.strip() and not line.startswith('===') and not line.startswith('collecting'):
            filtered_lines.append(line)
    
    clean_output = '\n'.join(filtered_lines)
    
    # Lire le README actuel
    with open('README.md', 'r') as f:
        content = f.read()
        
    # Trouver la section des tests
    start_marker = "```\n# Résultats des tests\n"
    end_marker = "```"
    
    if start_marker in content:
        # Mettre à jour la section existante
        start = content.find(start_marker)
        end = content.find(end_marker, start + len(start_marker))
        
        new_content = content[:start + len(start_marker)]
        new_content += clean_output
        new_content += content[end:]
    else:
        # Ajouter une nouvelle section
        new_content = content + "\n" + start_marker + clean_output + end_marker
    
    # Sauvegarder le nouveau README
    with open('README.md', 'w') as f:
        f.write(new_content)

@cli.command()
def version():
    """Met à jour la version dans la documentation"""
    # Lire la version depuis pyproject.toml
    with open('pyproject.toml', 'r') as f:
        for line in f:
            if line.startswith('version = '):
                version = line.split('"')[1]
                break
    
    # Mettre à jour le README
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Remplacer la version
    version_marker = "Version actuelle : "
    if version_marker in content:
        start = content.find(version_marker)
        end = content.find("\n", start)
        new_content = content[:start + len(version_marker)] + version + content[end:]
        
        with open('README.md', 'w') as f:
            f.write(new_content)

if __name__ == '__main__':
    cli() 