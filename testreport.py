import subprocess
from datetime import datetime
import html
import re
import click

def convert_ansi_to_html(text):
    """Convertit les codes ANSI en classes CSS."""
    ansi_to_css = {
        '\033[32m': '<span class="green">',    # Succès
        '\033[91m': '<span class="red">',      # Échec
        '\033[93m': '<span class="yellow">',   # Warning
        '\033[94m': '<span class="blue">',     # Info
        '\033[33m': '<span class="yellow">',   # Warning (autre code)
        '\033[0m': '</span>',                  # Reset
        '\033[1m': '<span class="bold">',      # Gras
        '\033[4m': '<span class="underline">', # Souligné
        'PASSED': '<span class="green">PASSED</span>',  # Tests réussis
        'FAILED': '<span class="red">FAILED</span>',    # Tests échoués
        'warnings summary': '<span class="yellow">warnings summary</span>',  # Titre des warnings
    }
    
    output = html.escape(text)
    for ansi, css in ansi_to_css.items():
        if isinstance(ansi, str):  # Pour les remplacements de texte exacts
            output = output.replace(ansi, css)
    return output

def extract_test_results(output):
    """Extrait le nombre de tests passés et le total des tests."""
    # Chercher le pattern "XX passed" à la fin du rapport
    passed_match = re.search(r'(\d+) passed', output)
    # Chercher le pattern "collected XX items"
    total_match = re.search(r'collected (\d+) items', output)
    
    if passed_match and total_match:
        passed = int(passed_match.group(1))
        total = int(total_match.group(1))
        return passed, total
    return None, None

def update_readme_with_report(test_output, timestamp):
    """Met à jour le README.md avec le rapport de test au format Markdown."""
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Extraire le nombre de tests passés
        passed, total = extract_test_results(test_output)
        test_summary = f"{passed}/{total} PASSED" if passed is not None else ""
        
        # Définir les marqueurs de début et fin
        start_marker = "<!-- START_TEST_REPORT -->"
        end_marker = "<!-- END_TEST_REPORT -->"
        
        # Convertir les codes ANSI en HTML avec classes CSS
        formatted_output = convert_ansi_to_html(test_output)
        
        # Créer le contenu au format Markdown avec styles inline
        markdown_content = f"""
### 🧪 Rapport de Tests - {timestamp} - {test_summary}

<div style="background-color: #1e1e1e; color: #ffffff; padding: 16px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; white-space: pre-wrap;">

<div style="font-family: monospace;">
{formatted_output.replace(
    '<span class="green">', '<span style="color: #4CAF50;">'
).replace(
    '<span class="red">', '<span style="color: #f44336;">'
).replace(
    '<span class="yellow">', '<span style="color: #ffeb3b;">'
).replace(
    '<span class="blue">', '<span style="color: #2196F3;">'
).replace(
    '<span class="bold">', '<span style="font-weight: bold;">'
).replace(
    '<span class="underline">', '<span style="text-decoration: underline;">'
)}
</div>

</div>
"""
        
        # Mettre à jour le titre dans la balise summary après REPORT_TITLE
        parts = readme_content.split('<!-- REPORT TITLE -->')
        if len(parts) > 1:
            # Remplacer le premier summary après REPORT_TITLE
            parts[1] = re.sub(
                r'<summary>.*?</summary>',
                f'<summary>🧪 Rapport de Tests - {timestamp} - {test_summary}</summary>',
                parts[1],
                count=1
            )
            readme_content = '<!-- REPORT TITLE -->'.join(parts)
        
        # Créer le pattern pour trouver la section à remplacer
        pattern = f"{start_marker}.*?{end_marker}"
        replacement = f"{start_marker}\n{markdown_content}\n{end_marker}"
        
        # Remplacer la section
        if start_marker in readme_content and end_marker in readme_content:
            new_content = re.sub(pattern, replacement, readme_content, flags=re.DOTALL)
        else:
            new_content = f"{readme_content}\n\n## Rapport de Tests\n\n{replacement}"
        
        # Sauvegarder le README mis à jour
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print("README.md mis à jour avec succès")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour du README: {str(e)}")
        return False

def generate_test_report():
    """Exécute les tests et retourne la sortie."""
    command = ["python", "scripts/test.py", "docker", "--test-only"]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests: {str(e)}")
        return None

def generate_html_report(test_output, timestamp):
    """Génère le rapport HTML."""
    html_output = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Rapport de Tests - {timestamp}</title>
    <style>
        body {{
            background-color: #2d2d2d;
            margin: 0;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .test-report {{
            background-color: #1e1e1e;
            color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 0 auto;
            max-width: 1200px;
        }}
        .test-report pre {{
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            white-space: pre-wrap;
            margin: 0;
        }}
        .header {{
            color: #ffffff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #444;
        }}
    </style>
</head>
<body>
    <div class="test-report">
        <div class="header">
            <h1>Rapport de Tests</h1>
            <p>Généré le {timestamp}</p>
        </div>
        <pre>{test_output}</pre>
    </div>
</body>
</html>
'''
    try:
        with open('test_report.html', 'w', encoding='utf-8') as f:
            f.write(html_output)
        return True
    except Exception as e:
        print(f"Erreur lors de la génération du rapport HTML: {str(e)}")
        return False

@click.group()
def cli():
    """Outil de génération de rapports de tests."""
    pass

@cli.command()
@click.option('--insert', is_flag=True, help='Insère uniquement le dernier rapport dans le README')
def report(insert):
    """Génère un rapport de tests."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if insert:
        # Lire le dernier rapport depuis test_report.html
        try:
            with open('test_report.html', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extraire le contenu du <pre>
                match = re.search(r'<pre>(.*?)</pre>', content, re.DOTALL)
                if match:
                    test_output = match.group(1)
                    update_readme_with_report(test_output, timestamp)
                else:
                    print("Impossible de trouver la sortie des tests dans test_report.html")
        except FileNotFoundError:
            print("Fichier test_report.html non trouvé")
    else:
        # Générer un nouveau rapport
        test_output = generate_test_report()
        if test_output:
            update_readme_with_report(test_output, timestamp)
            generate_html_report(test_output, timestamp)
            print("Rapports générés avec succès dans test_report.html et README.md")

@cli.command()
@click.argument('test_path', required=False)
@click.option('--insert', is_flag=True, help='Insère le dernier rapport sans relancer les tests')
def update_doc(test_path, insert):
    """Met à jour le README avec les résultats des tests."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if insert:
        try:
            # Lire le dernier rapport depuis test_report.html
            with open('test_report.html', 'r', encoding='utf-8') as f:
                content = f.read()
                # Extraire le contenu du <pre>
                match = re.search(r'<pre>(.*?)</pre>', content, re.DOTALL)
                if match:
                    test_output = match.group(1)
                    update_readme_with_report(test_output, timestamp)
                    print("Documentation mise à jour avec succès depuis le dernier rapport")
                    
                    # Afficher un résumé
                    passed, total = extract_test_results(test_output)
                    if passed is not None:
                        print(f"\nRésumé des tests : {passed}/{total} tests passés")
                else:
                    print("Impossible de trouver la sortie des tests dans test_report.html")
        except FileNotFoundError:
            print("Fichier test_report.html non trouvé")
    else:
        # Construire la commande de test
        command = ["python", "scripts/test.py", "docker", "--test-only"]
        if test_path:
            command.append(test_path)
        
        try:
            # Exécuter les tests
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.stdout:
                # Mettre à jour le README avec les résultats
                update_readme_with_report(result.stdout, timestamp)
                # Sauvegarder aussi le rapport HTML
                generate_html_report(result.stdout, timestamp)
                print("Documentation mise à jour avec succès")
                
                # Afficher un résumé
                passed, total = extract_test_results(result.stdout)
                if passed is not None:
                    print(f"\nRésumé des tests : {passed}/{total} tests passés")
            else:
                print("Aucune sortie de test à traiter")
                
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la documentation : {str(e)}")
            return False

if __name__ == "__main__":
    cli()